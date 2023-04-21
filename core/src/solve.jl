## types and functions
const Interpolation = LinearInterpolation{Vector{Float64}, Vector{Float64}, true, Float64}

"""
Store the connectivity information

graph: directed graph with vertices equal to ids
flow: store the flow on every edge
u_index: get the index into u from the basin id
edge_ids: get the external edge id from (src, dst)
"""
struct Connectivity
    graph::DiGraph{Int}
    flow::SparseMatrixCSC{Float64, Int}
    u_index::OrderedDict{Int, Int}
    edge_ids::OrderedDict{Tuple{Int, Int}, Int}
    Connectivity(graph, flow, u_index, edge_ids) =
        is_valid(graph, flow, u_index, edge_ids) ? new(graph, flow, u_index, edge_ids) :
        error("Invalid graph")
end

# TODO Add actual validation
function is_valid(
    graph::DiGraph{Int},
    flow::SparseMatrixCSC{Float64, Int},
    u_index::OrderedDict{Int, Int},
    edge_ids::OrderedDict{Tuple{Int, Int}, Int},
)
    return true
end

"""
Requirements:

* Must be positive: precipitation, evaporation, infiltration, drainage
* Index points to a Basin
* volume, area, level must all be positive and monotonic increasing.

Type parameter C indicates the content backing the StructVector, which can be a NamedTuple
of vectors or Arrow Tables, and is added to avoid type instabilities.
"""
struct Basin{C}
    precipitation::Vector{Float64}
    potential_evaporation::Vector{Float64}
    drainage::Vector{Float64}
    infiltration::Vector{Float64}
    # cache these to avoid recomputation
    current_area::Vector{Float64}
    current_level::Vector{Float64}
    # f(storage)
    area::Vector{Interpolation}
    level::Vector{Interpolation}
    # data source for parameter updates
    time::StructVector{BasinForcingV1, C, Int}
end

"""
    struct TabulatedRatingCurve{C}

Rating curve from level to discharge. The rating curve is a lookup table with linear
interpolation in between. Relation can be updated in time, which is done by moving data from
the `time` field into the `tables`, which is done in the `update_tabulated_rating_curve`
callback.

Type parameter C indicates the content backing the StructVector, which can be a NamedTuple
of Vectors or Arrow Primitives, and is added to avoid type instabilities.
"""
struct TabulatedRatingCurve{C}
    node_id::Vector{Int}
    tables::Vector{Interpolation}
    time::StructVector{TabulatedRatingCurveTimeV1, C, Int}
end

"""
Requirements:

* from: must be (Basin,) node
* to: must be (Basin,) node
"""
struct LinearLevelConnection
    node_id::Vector{Int}
    conductance::Vector{Float64}
end

"""
This is an extremely simple Manning-Gauckler reach connection.

* Length describes the reach length.
* roughness describes Manning's n in (SI units).

The profile is described by a trapezoid:

```
       \            /  ^
        \          /   | 
         \        /    | dz
 bottom   \______/     | 
 ^               <--->
 |  <------>       dx
 |    width
 |
 |
 + datum (e.g. MSL)
```

profile_slope = dx / dz.
A rectangular profile requires a slope of 0.0.

Requirements:

* from: must be (Basin,) node
* to: must be (Basin,) node
* length > 0
* roughess > 0
* profile_width >= 0
* profile_slope >= 0
* (profile_width == 0) xor (profile_slope == 0)
* slope_unit_length >= 0
"""
struct ManningConnection
    node_id::Vector{Int}
    length::Vector{Float64}
    n_inverted::Vector{Float64}
    profile_bottom::Vector{Float64}
    profile_width::Vector{Float64}
    profile_slope::Vector{Float64}
    profile_slope_unit_length::Vector{Float64}
end

ManningConnection() = ManningConnection(Int[], Float64[], Float64[], Float64[], Float64[], Float64[])

"""
Requirements:

* from: must be (TabulatedRatingCurve,) node
* to: must be (Basin,) node
* fraction must be positive.
"""
struct FractionalFlow
    node_id::Vector{Int}
    fraction::Vector{Float64}
end

"""
node_id: node ID of the LevelControl node
target_level: target level for the connected Basin
conductance: conductance on how quickly the target volume can be reached
"""
struct LevelControl
    node_id::Vector{Int}
    target_level::Vector{Float64}
    conductance::Vector{Float64}
end

"""
node_id: node ID of the Pump node
flow_rate: target flow rate
"""
struct Pump
    node_id::Vector{Int}
    flow_rate::Vector{Float64}
end

# TODO Automatically add all nodetypes here
struct Parameters
    starttime::DateTime
    connectivity::Connectivity
    basin::Basin
    linear_level_connection::LinearLevelConnection
    tabulated_rating_curve::TabulatedRatingCurve
    fractional_flow::FractionalFlow
    level_control::LevelControl
    pump::Pump
end

"""
Linearize the evaporation flux when at small water depths
Currently at less than 0.1 m.
"""
function formulate!(du::AbstractVector, basin::Basin, u::AbstractVector, t::Real)::Nothing
    for i in eachindex(du)
        storage = u[i]
        area = basin.area[i](storage)
        level = basin.level[i](storage)
        basin.current_area[i] = area
        basin.current_level[i] = level
        bottom = first(basin.level[i].u)
        fixed_area = median(basin.area[i].u)
        depth = max(level - bottom, 0.0)
        reduction_factor = min(depth, 0.1) / 0.1

        precipitation = fixed_area * basin.precipitation[i]
        evaporation = area * reduction_factor * basin.potential_evaporation[i]
        drainage = basin.drainage[i]
        infiltration = reduction_factor * basin.infiltration[i]

        du[i] += precipitation - evaporation + drainage - infiltration
    end
    return nothing
end

"""
Directed graph: outflow is positive!
"""
function formulate!(
    connectivity::Connectivity,
    linear_level_connection::LinearLevelConnection,
    level,
)::Nothing
    (; graph, flow, u_index) = connectivity
    (; node_id, conductance) = linear_level_connection
    for (i, id) in enumerate(node_id)
        basin_a_id = only(inneighbors(graph, id))
        basin_b_id = only(outneighbors(graph, id))
        q = conductance[i] * (level[u_index[basin_a_id]] - level[u_index[basin_b_id]])
        flow[basin_a_id, id] = q
        flow[id, basin_b_id] = q
    end
    return nothing
end

"""
Directed graph: outflow is positive!
"""
function formulate!(
    connectivity::Connectivity,
    tabulated_rating_curve::TabulatedRatingCurve,
    level,
)::Nothing
    (; graph, flow, u_index) = connectivity
    (; node_id, tables) = tabulated_rating_curve
    for (i, id) in enumerate(node_id)
        upstream_basin_id = only(inneighbors(graph, id))
        downstream_ids = outneighbors(graph, id)
        q = tables[i](level[u_index[upstream_basin_id]])
        flow[upstream_basin_id, id] = q
        for downstream_id in downstream_ids
            flow[id, downstream_id] = q
        end
    end
    return nothing
end


"""
Gauckler-Manning formula:

V = (1 / n) R_h ^ (2/3) S ^ (1/2)

Where:

    * V is the cross-sectional average velocity.
    * n is the Gauckler-Manning coefficient.
    * R_h is the hydraulic radius.
    * S is the hydraulic gradient.
    
R_h = A / P

    * Where A is the cross-sectional area.
    * P is the wetted perimeter.

The connection may go dry if the head of either basin falls below the profile
bottom. This is a very simple "upstream" formulation, it computes the reach
profile based on the basin with the highest head.
"""
function formulate!(
    connectivity::Connectivity,
    manning_connection::ManningConnection,
    level,
)::Nothing
    # TODO: we can precompute a great deal of values.
    (; graph, flow, u_index) = connectivity
    (; node_id, length, n_inverted, profile_bottom, profile_width, profile_slope, unit_length) = manning_connection
    for (i, id) in enumerate(node_id)
        basin_a_id = only(inneighbors(graph, id))
        basin_b_id = only(outneighbors(graph, id))
    
        # Compute the hydraulic slope
        # TODO: should the basin bottom be used instead?
        level_a = max(profile_bottom[i], level[u_index[basin_a_id]])
        level_b = max(profile_bottom[i], level[u_index[basin_b_id]])
        S = (level_a - level_b) / length[i]

        # Compute cross sectional area and hydraulic radius
        upstream_level = max(level_a, level_b)
        depth = upstream_level - profile_bottom[i] 
        A = profile_width * depth * depth * profile_slope[i]
        P = profile_width + 2.0 * depth * unit_length[i]
        R_h = A / P
 
        # Gauckler-Manning Formula
        q = A * n_inverted[i] * R_h ^ (2/3) * sqrt(S)
        flow[basin_a_id, id] = q
        flow[id, basin_b_id] = q
    end
    return nothing
end

function formulate!(connectivity::Connectivity, fractional_flow::FractionalFlow)::Nothing
    (; graph, flow) = connectivity
    (; node_id, fraction) = fractional_flow
    for (i, id) in enumerate(node_id)
        upstream_id = only(inneighbors(graph, id))
        downstream_id = only(outneighbors(graph, id))
        flow[id, downstream_id] = flow[upstream_id, id] * fraction[i]
    end
    return nothing
end

function formulate!(connectivity::Connectivity, level_control::LevelControl, level)::Nothing
    (; graph, flow, u_index) = connectivity
    (; node_id, target_level, conductance) = level_control
    for (i, id) in enumerate(node_id)  # TODO eachindex
        # support either incoming or outgoing edges
        for basin_id in inneighbors(graph, id)
            flow[basin_id, id] =
                conductance[i] * (level[u_index[basin_id]] - target_level[i])
        end
        for basin_id in outneighbors(graph, id)
            flow[id, basin_id] =
                conductance[i] * (target_level[i] - level[u_index[basin_id]])
        end
    end
    return nothing
end

function formulate!(connectivity::Connectivity, pump::Pump, u)::Nothing
    (; graph, flow, u_index) = connectivity
    (; node_id, flow_rate) = pump
    for (id, rate) in zip(node_id, flow_rate)
        src_id = only(inneighbors(graph, id))
        dst_id = only(outneighbors(graph, id))
        # negative flow_rate means pumping against edge direction
        intake_id = rate >= 0 ? src_id : dst_id
        basin_idx = get(u_index, intake_id, 0)
        @assert basin_idx != 0 "Pump intake not a Basin"
        storage = u[basin_idx]
        reduction_factor = min(storage, 10.0) / 10.0
        q = reduction_factor * rate
        flow[src_id, id] = q
        flow[id, dst_id] = q
    end
    return nothing
end

function formulate!(du, connectivity::Connectivity)::Nothing
    # loop over basins
    # subtract all outgoing flows
    # add all ingoing flows
    (; graph, flow, u_index) = connectivity
    for (basin_id, i) in pairs(u_index)
        for in_id in inneighbors(graph, basin_id)
            du[i] += flow[in_id, basin_id]
        end
        for out_id in outneighbors(graph, basin_id)
            du[i] -= flow[basin_id, out_id]
        end
    end
    return nothing
end

function water_balance!(du, u, p, t)::Nothing
    (;
        connectivity,
        basin,
        linear_level_connection,
        tabulated_rating_curve,
        fractional_flow,
        level_control,
        pump,
    ) = p

    du .= 0.0
    nonzeros(connectivity.flow) .= 0.0

    # ensures current_level and current_area are current
    formulate!(du, basin, u, t)

    # First formulate intermediate flows
    formulate!(connectivity, linear_level_connection, basin.current_level)
    formulate!(connectivity, tabulated_rating_curve, basin.current_level)
    formulate!(connectivity, fractional_flow)
    formulate!(connectivity, level_control, basin.current_level)
    formulate!(connectivity, pump, u)

    # Now formulate du
    formulate!(du, connectivity)

    # Negative storage musn't decrease, based on Shampine's et. al. advice
    # https://docs.sciml.ai/DiffEqCallbacks/stable/step_control/#DiffEqCallbacks.PositiveDomain
    for i in eachindex(u)
        if u[i] < 0
            du[i] = max(du[i], 0.0)
        end
    end

    return nothing
end

function track_waterbalance!(u, t, integrator)::Nothing
    (; p, tprev, uprev) = integrator
    dt = t - tprev
    du = u - uprev
    p.storage_diff .+= du
    p.precipitation.total .+= p.precipitation.value .* dt
    p.evaporation.total .+= p.evaporation.value .* dt
    p.infiltration.total .+= p.infiltration.value .* dt
    p.drainage.total .+= p.drainage.value .* dt
    return nothing
end
