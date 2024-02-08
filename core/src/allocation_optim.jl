"""
Add a term to the expression of the objective function corresponding to
the demand of a user.
"""
function add_user_term!(
    ex::Union{JuMP.QuadExpr, JuMP.AffExpr},
    edge::Tuple{NodeID, NodeID},
    objective_type::Symbol,
    demand::Float64,
    model::AllocationModel,
)::Nothing
    (; problem) = model
    F = problem[:F]
    F_edge = F[edge]
    node_id_user = edge[2]

    if objective_type == :quadratic_absolute
        # Objective function ∑ (F - d)^2
        JuMP.add_to_expression!(ex, 1, F_edge, F_edge)
        JuMP.add_to_expression!(ex, -2 * demand, F_edge)
        JuMP.add_to_expression!(ex, demand^2)

    elseif objective_type == :quadratic_relative
        # Objective function ∑ (1 - F/d)^2
        if demand ≈ 0
            return nothing
        end
        JuMP.add_to_expression!(ex, 1.0 / demand^2, F_edge, F_edge)
        JuMP.add_to_expression!(ex, -2.0 / demand, F_edge)
        JuMP.add_to_expression!(ex, 1.0)

    elseif objective_type == :linear_absolute
        # Objective function ∑ |F - d|
        JuMP.set_normalized_rhs(problem[:abs_positive][node_id_user], -demand)
        JuMP.set_normalized_rhs(problem[:abs_negative][node_id_user], demand)

    elseif objective_type == :linear_relative
        # Objective function ∑ |1 - F/d|
        JuMP.set_normalized_coefficient(
            problem[:abs_positive][node_id_user],
            F_edge,
            iszero(demand) ? 0 : 1 / demand,
        )
        JuMP.set_normalized_coefficient(
            problem[:abs_negative][node_id_user],
            F_edge,
            iszero(demand) ? 0 : -1 / demand,
        )
    else
        error("Invalid allocation objective type $objective_type.")
    end
    return nothing
end

"""
Set the objective for the given priority.
For an objective with absolute values this also involves adjusting constraints.
"""
function set_objective_priority!(
    allocation_model::AllocationModel,
    p::Parameters,
    t::Float64,
    priority_idx::Int,
)::Nothing
    (; objective_type, problem, allocation_network_id) = allocation_model
    (; graph, user, allocation, basin) = p
    (; demand, node_id) = user
    (; main_network_connections, subnetwork_demands) = allocation
    edge_ids = graph[].edge_ids[allocation_network_id]
    node_ids = graph[].node_ids[allocation_network_id]

    F = problem[:F]
    if objective_type in [:quadratic_absolute, :quadratic_relative]
        ex = JuMP.QuadExpr()
    elseif objective_type in [:linear_absolute, :linear_relative]
        ex = JuMP.AffExpr()
        ex += sum(problem[:F_abs])
    end

    demand_max = 0.0

    # Terms for subnetworks as users
    if is_main_network(allocation_network_id)
        for connections_subnetwork in main_network_connections
            for connection in connections_subnetwork
                d = subnetwork_demands[connection][priority_idx]
                demand_max = max(demand_max, d)
                add_user_term!(ex, connection, objective_type, d, allocation_model)
            end
        end
    end

    # Terms for user nodes
    for edge_id in edge_ids
        node_id_user = edge_id[2]
        if graph[node_id_user].type != :user
            continue
        end

        user_idx = findsorted(node_id, node_id_user)
        d = demand[user_idx][priority_idx](t)
        demand_max = max(demand_max, d)
        add_user_term!(ex, edge_id, objective_type, d, allocation_model)
    end

    # Add flow cost
    if objective_type == :linear_absolute
        cost_per_flow = 0.5 / length(F)
        for flow in F
            JuMP.add_to_expression!(ex, cost_per_flow * flow)
        end
    elseif objective_type == :linear_relative
        if demand_max > 0.0
            cost_per_flow = 0.5 / (demand_max * length(F))
            for flow in F
                JuMP.add_to_expression!(ex, cost_per_flow * flow)
            end
        end
    end

    # Add
    F_basin = problem[:F_basin]
    for node_id in only(F_basin.axes)
        if priority_idx == findsorted
            d = get_basin_demand(allocation_model, u, p, t, node_id)
        end
    end

    new_objective = JuMP.@expression(problem, ex)
    JuMP.@objective(problem, Min, new_objective)
    return nothing
end

"""
Assign the allocations to the users as determined by the solution of the allocation problem.
"""
function assign_allocations!(
    allocation_model::AllocationModel,
    p::Parameters,
    t::Float64,
    priority_idx::Int;
    collect_demands::Bool = false,
)::Nothing
    (; problem, allocation_network_id) = allocation_model
    (; graph, user, allocation) = p
    (;
        subnetwork_demands,
        subnetwork_allocateds,
        allocation_network_ids,
        main_network_connections,
    ) = allocation
    (; record) = user
    edge_ids = graph[].edge_ids[allocation_network_id]
    main_network_source_edges = get_main_network_connections(p, allocation_network_id)
    F = problem[:F]
    for edge_id in edge_ids
        # If this edge is a source edge from the main network to a subnetwork,
        # and demands are being collected, add its flow to the demand of this edge
        if collect_demands &&
           graph[edge_id...].allocation_network_id_source == allocation_network_id &&
           edge_id ∈ main_network_source_edges
            allocated = JuMP.value(F[edge_id])
            subnetwork_demands[edge_id][priority_idx] += allocated
        end

        user_node_id = edge_id[2]

        if graph[user_node_id].type == :user
            allocated = JuMP.value(F[edge_id])
            user_idx = findsorted(user.node_id, user_node_id)
            user.allocated[user_idx][priority_idx] = allocated

            # Save allocations to record
            push!(record.time, t)
            push!(record.allocation_network_id, allocation_model.allocation_network_id)
            push!(record.user_node_id, Int(user_node_id))
            push!(record.priority, allocation.priorities[priority_idx])
            push!(record.demand, user.demand[user_idx][priority_idx](t))
            push!(record.allocated, allocated)
            # TODO: This is now the last abstraction before the allocation update,
            # should be the average abstraction since the last allocation solve
            push!(
                record.abstracted,
                get_flow(graph, inflow_id(graph, user_node_id), user_node_id, 0),
            )
        end
    end

    # Write the flows to the subnetworks as allocated flows
    # in the allocation object
    if is_main_network(allocation_network_id)
        for (allocation_network_id, main_network_source_edges) in
            zip(allocation_network_ids, main_network_connections)
            if is_main_network(allocation_network_id)
                continue
            end
            for edge_id in main_network_source_edges
                subnetwork_allocateds[edge_id][priority_idx] = JuMP.value(F[edge_id])
            end
        end
    end
    return nothing
end

"""
Adjust the source flows.
"""
function adjust_source_capacities!(
    allocation_model::AllocationModel,
    p::Parameters,
    priority_idx::Int;
    collect_demands::Bool = false,
)::Nothing
    (; problem) = allocation_model
    (; graph, allocation) = p
    (; allocation_network_id) = allocation_model
    (; subnetwork_allocateds) = allocation
    edge_ids = graph[].edge_ids[allocation_network_id]
    source_constraints = problem[:source]
    F = problem[:F]

    main_network_source_edges = get_main_network_connections(p, allocation_network_id)

    for edge_id in edge_ids
        if graph[edge_id...].allocation_network_id_source == allocation_network_id
            # If it is a source edge for this allocation problem
            if priority_idx == 1
                # If the optimization was just started, i.e. sources have to be reset
                if edge_id in main_network_source_edges
                    if collect_demands
                        # Set the source capacity to effectively unlimited if subnetwork demands are being collected
                        source_capacity = Inf
                    else
                        # Set the source capacity to the value allocated to the subnetwork over this edge
                        source_capacity = subnetwork_allocateds[edge_id][priority_idx]
                    end
                else
                    # Reset the source to the current flow from the physical layer.
                    source_capacity = get_flow(graph, edge_id..., 0)
                end
                JuMP.set_normalized_rhs(
                    source_constraints[edge_id],
                    # It is assumed that the allocation procedure does not have to be differentiated.
                    source_capacity,
                )
            else
                # Subtract the allocated flow from the source.
                JuMP.set_normalized_rhs(
                    source_constraints[edge_id],
                    JuMP.normalized_rhs(source_constraints[edge_id]) -
                    JuMP.value(F[edge_id]),
                )
            end
        end
    end
    return nothing
end

"""
Set the values of the edge capacities. 2 cases:
- Before the first allocation solve, set the edge capacities to their full capacity;
- Before an allocation solve, subtract the flow used by allocation for the previous priority
  from the edge capacities.
"""
function adjust_edge_capacities!(
    allocation_model::AllocationModel,
    p::Parameters,
    priority_idx::Int,
)::Nothing
    (; graph) = p
    (; problem, capacity, allocation_network_id) = allocation_model
    edge_ids = graph[].edge_ids[allocation_network_id]
    constraints_capacity = problem[:capacity]
    F = problem[:F]

    main_network_source_edges = get_main_network_connections(p, allocation_network_id)

    for edge_id in edge_ids
        c = capacity[edge_id...]

        # These edges have no capacity constraints:
        # - With infinite capacity
        # - Being a source from the main network to a subnetwork
        if isinf(c) || edge_id ∈ main_network_source_edges
            continue
        end

        if priority_idx == 1
            # Before the first allocation solve, set the edge capacities to their full capacity
            JuMP.set_normalized_rhs(constraints_capacity[edge_id], c)
        else
            # Before an allocation solve, subtract the flow used by allocation for the previous priority
            # from the edge capacities
            JuMP.set_normalized_rhs(
                constraints_capacity[edge_id],
                JuMP.normalized_rhs(constraints_capacity[edge_id]) - JuMP.value(F[edge_id]),
            )
        end
    end
end

function get_basin_data(
    allocation_model::AllocationModel,
    p::Parameters,
    u::ComponentVector,
    node_id::NodeID,
)
    (; graph, basin, allocation_level_control) = p
    (; Δt_allocation) = allocation_model
    influx = get_flow(graph, node_id, 0.0)
    _, basin_idx = id_index(basin.node_id, node_id)
    storage_basin = u.storage[basin_idx]
    allocation_level_control_node_id =
        first(inneighbor_labels_type(graph, node_id, EdgeType.control))
    allocation_level_control_idx =
        findsorted(allocation_level_control.node_id, allocation_level_control_node_id)
    return storage_basin, Δt_allocation, influx, allocation_level_control_idx, basin_idx
end

function get_basin_capacity(
    allocation_model::AllocationModel,
    u::ComponentVector,
    p::Parameters,
    t::Float64,
    node_id::NodeID,
)::Float64
    (; allocation_level_control) = p
    storage_basin, Δt_allocation, influx, allocation_level_control_idx, basin_idx =
        get_basin_data(allocation_model, p, u, node_id)
    level_max = allocation_level_control.max_level[allocation_level_control_idx](t)
    storage_max = get_storage_from_level(p.basin, basin_idx, level_max)
    return max(0.0, (storage_basin - storage_max) / Δt_allocation + influx)
end

function get_basin_demand(
    allocation_model::AllocationModel,
    u::ComponentVector,
    p::Parameters,
    t::Float64,
    node_id::NodeID,
)::Float64
    (; allocation_level_control) = p
    storage_basin, Δt_allocation, influx, allocation_level_control_idx, basin_idx =
        get_basin_data(allocation_model, p, u, node_id)
    level_min = allocation_level_control.min_level[allocation_level_control_idx](t)
    storage_min = get_storage_from_level(p.basin, basin_idx, level_min)
    return max(0.0, (storage_basin - storage_min) / Δt_allocation - influx)
end

function adjust_basin_capacities!(
    allocation_model::AllocationModel,
    u::ComponentVector,
    p::Parameters,
    t::Float64,
    priority_idx::Int,
)::Nothing
    (; problem) = allocation_model
    constraints_basin_flow = problem[:basin_flow]
    F_basin = problem[:F_basin]

    for node_id in only(constraints_basin_flow.axes)
        constraint = constraints_basin_flow[node_id]
        if priority_idx == 1
            JuMP.set_normalized_rhs(
                constraint,
                get_basin_capacity(allocation_model, u, p, t, node_id),
            )
        else
            JuMP.set_normalized_rhs(
                constraint,
                JuMP.normalized_rhs(constraint) - JuMP.value(F_basin[node_id]),
            )
        end
    end

    return nothing
end

"""
Save the allocation flows per basin physical edge.
"""
function save_allocation_flows!(
    p::Parameters,
    t::Float64,
    allocation_model::AllocationModel,
    priority::Int,
    collect_demands::Bool,
)::Nothing
    (; problem, allocation_network_id) = allocation_model
    (; allocation, graph) = p
    (; record) = allocation
    F = problem[:F]

    # Edge flows
    for allocation_edge in first(F.axes)
        flow = JuMP.value(F[allocation_edge])
        edge_metadata = graph[allocation_edge...]
        (; node_ids) = edge_metadata

        for i in eachindex(node_ids)[1:(end - 1)]
            push!(record.time, t)
            push!(record.edge_id, edge_metadata.id)
            push!(record.from_node_id, node_ids[i])
            push!(record.to_node_id, node_ids[i + 1])
            push!(record.allocation_network_id, allocation_network_id)
            push!(record.priority, priority)
            push!(record.flow, flow)
            push!(record.collect_demands, collect_demands)
        end
    end

    # Basin flows
    for node_id in graph[].node_id[allocation_network_id]
        if graph[node_id].type == :basin
            flow = ...
            push!(record.time, t)
            push!(record.edge_id, 0)
            push!(record.from_node_id, node_id)
            push!(record.to_node_id, node_id)
            push!(record.allocation_network_id, allocation_network_id)
            push!(record.priority, priority)
            push!(record.flow, flow)
            push!(record.collect_demands, collect_demands)
        end
    end

    return nothing
end

"""
Update the allocation optimization problem for the given subnetwork with the problem state
and flows, solve the allocation problem and assign the results to the users.
"""
function allocate!(
    p::Parameters,
    allocation_model::AllocationModel,
    t::Float64,
    u::ComponentVector;
    collect_demands::Bool = false,
)::Nothing
    (; allocation) = p
    (; problem, allocation_network_id) = allocation_model
    (; priorities, subnetwork_demands) = allocation

    main_network_source_edges = get_main_network_connections(p, allocation_network_id)

    if collect_demands
        for main_network_connection in keys(subnetwork_demands)
            if main_network_connection in main_network_source_edges
                subnetwork_demands[main_network_connection] .= 0.0
            end
        end
    end

    for priority_idx in eachindex(priorities)
        adjust_source_capacities!(allocation_model, p, priority_idx; collect_demands)

        # Subtract the flows used by the allocation of the previous priority from the capacities of the edges
        # or set edge capacities if priority_idx = 1
        adjust_edge_capacities!(allocation_model, p, priority_idx)

        adjust_basin_capacities!(allocation_model, u, p, t, priority_idx)

        # Set the objective depending on the demands
        # A new objective function is set instead of modifying the coefficients
        # of an existing objective function because this is not supported for
        # quadratic terms:
        # https://jump.dev/JuMP.jl/v1.16/manual/objective/#Modify-an-objective-coefficient
        set_objective_priority!(allocation_model, p, t, priority_idx)

        # Solve the allocation problem for this priority
        JuMP.optimize!(problem)
        @debug JuMP.solution_summary(problem)
        if JuMP.termination_status(problem) !== JuMP.OPTIMAL
            (; allocation_network_id) = allocation_model
            priority = priorities[priority_idx]
            error(
                "Allocation of subnetwork $allocation_network_id, priority $priority coudn't find optimal solution.",
            )
        end

        # Assign the allocations to the users for this priority
        assign_allocations!(allocation_model, p, t, priority_idx; collect_demands)

        # Save the flows over all edges in the subnetwork
        save_allocation_flows!(
            p,
            t,
            allocation_model,
            priorities[priority_idx],
            collect_demands,
        )
    end
end
