"Change a dictionary entry to be relative to `dir` if is is not an abolute path"
function relative_path!(dict, key, dir)
    if haskey(dict, key)
        val = dict[key]
        dict[key] = normpath(dir, val)
    end
    return dict
end

"Make all possible path entries relative to `dir`."
function relative_paths!(dict, dir)
    relative_path!(dict, "forcing", dir)
    relative_path!(dict, "state", dir)
    relative_path!(dict, "static", dir)
    relative_path!(dict, "profile", dir)
    relative_path!(dict, "edge", dir)
    relative_path!(dict, "node", dir)
    relative_path!(dict, "waterbalance", dir)
    if haskey(dict, "modflow")
        relative_path!(dict["modflow"], "simulation", dir)
        relative_path!(dict["modflow"]["models"]["gwf"], "dataset", dir)
    end
    # Append pkg version to cache filename
    if haskey(dict, "cache")
        v = pkgversion(Ribasim)
        n, ext = splitext(dict["cache"])
        dict["cache"] = "$(n)_$(string(v))$ext"
        relative_path!(dict, "cache", dir)
    end
    return dict
end

"Parse the TOML configuration file, updating paths to be relative to the TOML file."
function parsefile(config_file::AbstractString)
    config = TOML.parsefile(config_file)
    dir = dirname(config_file)
    return relative_paths!(config, dir)
end

function BMI.initialize(T::Type{Register}, config_file::AbstractString)
    config = TOML.parsefile(config_file)
    dir = dirname(config_file)
    config = relative_paths!(config, dir)
    BMI.initialize(T, config)
end

# create a subgraph, with fractions on the edges we use
function subgraph(network, ids)
    # defined for every edge in the ply file
    fractions_all = network.edge_table.fractions
    lsw_all = Int.(network.node_table.location)
    graph_all = network.graph
    lsw_indices = [findfirst(==(lsw_id), lsw_all) for lsw_id in ids]
    graph, _ = induced_subgraph(graph_all, lsw_indices)

    return graph, graph_all, fractions_all, lsw_all
end

# Read into memory for now with read, to avoid locking the file, since it mmaps otherwise.
# We could pass Mmap.mmap(path) ourselves and make sure it gets closed, since Arrow.Table
# does not have an io handle to close.
read_table(entry::AbstractString) = Arrow.Table(read(entry))

function read_table(entry)
    @assert Tables.istable(entry)
    return entry
end

"Create an extra column in the forcing which is 0 or the index into the system parameters"
function find_param_index(forcing, p_vars, p_ids)
    (; variable, id) = forcing
    # 0 means not in the model, skip
    param_index = zeros(Int, length(variable))

    for i in eachindex(variable, id, param_index)
        var = variable[i]
        id_ = id[i]
        for (j, (p_var, p_id)) in enumerate(zip(p_vars, p_ids))
            if (p_var, p_id) == (var, id_)
                param_index[i] = j
            end
        end
    end
    return param_index
end

"Get the indices of modflow-coupled LSWs into the system state vector"
function find_volume_index(mf_locs, u_vars, u_locs)
    volume_index = zeros(Int, length(mf_locs))

    for (i, mf_loc) in enumerate(mf_locs)
        for (j, (u_var, u_loc)) in enumerate(zip(u_vars, u_locs))
            if (u_var, u_loc) == (Symbol("lsw.S"), mf_loc)
                volume_index[i] = j
            end
        end
        @assert volume_index[i] != 0
    end
    return volume_index
end

function find_modflow_indices(mf_locs, p_vars, p_locs)
    drainage_index = zeros(Int, length(mf_locs))
    infiltration_index = zeros(Int, length(mf_locs))

    for (i, mf_loc) in enumerate(mf_locs)
        for (j, (p_var, p_loc)) in enumerate(zip(p_vars, p_locs))
            if (p_var, p_loc) == (Symbol("lsw.drainage"), mf_loc)
                drainage_index[i] = j
            elseif (p_var, p_loc) == (Symbol("lsw.infiltration"), mf_loc)
                infiltration_index[i] = j
            end
        end
        @assert drainage_index[i] != 0
        @assert infiltration_index[i] != 0
    end
    return drainage_index, infiltration_index
end

"Collect the indices, locations and names of all integrals, for writing to output"
function prepare_waterbalance(syms::Vector{Symbol})
    # fluxes integrated over time
    wbal_entries = (; location = Int[], variable = String[], index = Int[], flip = Bool[])
    # initial values are handled in callback
    prev_state = fill(NaN, length(syms))
    for (i, sym) in enumerate(syms)
        varname, location = parsename(sym)
        varname = String(varname)
        if endswith(varname, ".sum.x")
            variable = replace(varname, r".sum.x$" => "")
            # flip the sign of the loss terms
            flip = if endswith(variable, ".x.Q")
                true
            elseif variable in ("weir.Q", "lsw.Q_eact", "lsw.infiltration_act")
                true
            else
                false
            end
            push!(wbal_entries.location, location)
            push!(wbal_entries.variable, variable)
            push!(wbal_entries.index, i)
            push!(wbal_entries.flip, flip)
        elseif varname == "lsw.S"
            push!(wbal_entries.location, location)
            push!(wbal_entries.variable, varname)
            push!(wbal_entries.index, i)
            push!(wbal_entries.flip, false)
        end
    end
    return wbal_entries, prev_state
end

function getstate(integrator, s)::Real
    (; u) = integrator
    (; syms) = integrator.sol.prob.f
    sym = Symbolics.getname(s)::Symbol
    i = findfirst(==(sym), syms)
    if i === nothing
        error(lazy"not found: $sym")
    end
    return u[i]
end

function param(integrator, s)::Real
    (; p) = integrator
    (; paramsyms) = integrator.sol.prob.f
    sym = Symbolics.getname(s)::Symbol
    i = findfirst(==(sym), paramsyms)
    if i === nothing
        error(lazy"not found: $sym")
    end
    return p[i]
end

function param!(integrator, s, x::Real)::Real
    (; p) = integrator
    (; paramsyms) = integrator.sol.prob.f
    sym = Symbolics.getname(s)::Symbol
    i = findfirst(==(sym), paramsyms)
    if i === nothing
        error(lazy"not found: $sym")
    end
    return p[i] = x
end

"""Parse the system parameters into a vector of variables and a vector of IDs in the same
order. These can be used to map forcing data to the right index in the integrator's
parameter vector p."""
function parse_paramsyms(paramsyms)::Tuple{Vector{String}, Vector{Int}}
    param_vars = String[]
    param_ids = Int[]
    for paramsym in paramsyms
        varsym, id = parsename(paramsym)
        push!(param_vars, String(varsym))
        push!(param_ids, id)
    end
    return param_vars, param_ids
end

function BMI.initialize(T::Type{Register}, config::AbstractDict)

    # Δt for periodic update frequency, including user horizons
    Δt = Float64(config["update_timestep"])
    starttime = DateTime(config["starttime"])
    endtime = DateTime(config["endtime"])
    run_modflow = get(config, "run_modflow", false)::Bool

    (; ids, edge, node, state, static, profile, forcing) = load_data(config, starttime,
                                                                     endtime)
    nodetypes = Dictionary(node.id, node.node)

    function allocate!(integrator)
        # TODO bring back user allocation
        (; t, p) = integrator

        # for (i, id) in enumerate(ids)
        #     S = getstate(integrator, name_t(:lsw, id, :S))
        #     # forcing values
        #     P = param(integrator, name_t(:lsw, id, :P))
        # end

        # save!(param_hist, t, p)
        return nothing
    end

    # We update parameters with forcing data. Only the current value per parameter is
    # stored in the solution object, so we track the history ourselves.
    param_hist = ForwardFill(Float64[], Vector{Float64}[])
    tspan = (datetime2unix(starttime), datetime2unix(endtime))

    if haskey(config, "cache") && isfile(config["cache"])
        @info "Using cached problem" path=config["cache"]
        prob = deserialize(config["cache"])
    else
        sysdict = create_nodes(node, state, profile, static)
        connect_eqs = connect_systems(edge, sysdict)
        output_eqs, output_systems = add_waterbalance_cumulatives(sysdict, nodetypes,
                                                                  waterbalance_terms)
        inputs = find_unbound_inputs(sysdict, nodetypes, input_terms)

        # combine the network and output systems into one
        systems = vcat(collect(sysdict), output_systems)
        eqs = vcat(connect_eqs, output_eqs)
        @named sys = ODESystem(eqs, t, [], []; systems)

        # TODO use input_idxs rather than parse_paramsyms
        sim, input_idxs = structural_simplify(sys, (; inputs, outputs = []))

        prob = ODAEProblem(sim, [], tspan; sparse = true)
        if haskey(config, "cache")
            @info "Caching initialized problem" path=config["cache"]
            open(config["cache"], "w") do io
                serialize(io, prob)
            end
        end
    end

    # add (t) to make it the same with the syms as stored in the integrator
    syms = [Symbol(getname(s), "(t)") for s in states(prob.f.sys)]
    paramsyms = getname.(parameters(prob.f.sys))
    # split out the variables and IDs to make it easier to find the right param index
    param_vars, param_ids = parse_paramsyms(paramsyms)
    # add the system's parameter index to the forcing table
    param_vars, param_ids = parse_paramsyms(paramsyms)
    param_index = find_param_index(forcing, param_vars, param_ids)

    used_param_index = filter(!=(0), param_index)
    used_rows = findall(!=(0), param_index)
    # consider usign views here
    used_time = forcing.time[used_rows]
    @assert issorted(used_time) "time column in forcing must be sorted"
    used_time_unix = datetime2unix.(used_time)
    used_value = forcing.value[used_rows]
    # this is how often we need to callback
    used_time_uniq = unique(used_time)

    # find the range of the current timestep, and the associated parameter indices,
    # and update all the corresponding parameter values
    # captures used_time_unix, used_param_index, used_value, param_hist
    function update_forcings!(integrator)
        (; t, p) = integrator
        r = searchsorted(used_time_unix, t)
        i = used_param_index[r]
        v = used_value[r]
        p[i] .= v
        save!(param_hist, t, p)
        return nothing
    end

    if run_modflow
        # initialize Modflow model
        config_modflow = config["modflow"]
        Δt_modflow = Float64(config_modflow["timestep"])
        rme = RibasimModflowExchange(config_modflow, ids)

        # get the index into the system state vector for each coupled LSW
        mf_locs = collect(keys(rme.basin_volume))
        u_vars = first.(parsename.(syms))
        u_locs = last.(parsename.(syms))
        volume_index = find_volume_index(mf_locs, u_vars, u_locs)

        # similarly for the index into the system parameter vector
        pmf_vars = first.(parsename.(paramsyms))
        pmf_locs = last.(parsename.(paramsyms))
        drainage_index, infiltration_index = find_modflow_indices(mf_locs, pmf_vars,
                                                                  pmf_locs)
    else
        rme = nothing
    end

    # captures volume_index, drainage_index, infiltration_index, rme, tspan
    function exchange_modflow!(integrator)
        (; t, u, p) = integrator

        # set basin_volume from Ribasim
        # mutate the underlying vector, we know the keys are equal
        rme.basin_volume.values .= u[volume_index]

        # convert basin_volume to modflow levels
        exchange_ribasim_to_modflow!(rme)

        # run modflow timestep
        first_step = t == tspan[begin]
        update!(rme.modflow, first_step)

        # sets basin_infiltration and basin_drainage from modflow
        exchange_modflow_to_ribasim!(rme)

        # put basin_infiltration and basin_drainage into Ribasim
        # convert modflow m3/d to Ribasim m3/s, both positive
        # TODO don't use infiltration and drainage from forcing
        p[drainage_index] .= rme.basin_drainage.values ./ 86400.0
        p[infiltration_index] .= rme.basin_infiltration.values ./ 86400.0
    end

    wbal_entries, prev_state = prepare_waterbalance(syms)
    waterbalance = DataFrame(time = DateTime[], variable = String[], location = Int[],
                             value = Float64[])
    # captures waterbalance, wbal_entries, prev_state, tspan
    function write_output!(integrator)
        (; t, u) = integrator
        time = unix2datetime(t)
        first_step = t == tspan[begin]
        for (; variable, location, index, flip) in Tables.rows(wbal_entries)
            if variable == "lsw.S"
                S = u[index]
                if first_step
                    prev_state[index] = S
                end
                value = prev_state[index] - S
                prev_state[index] = S
            else
                value = flip ? -u[index] : u[index]
                u[index] = 0.0  # reset cumulative back to 0 to get m3 since previous record
            end
            record = (; time, variable, location, value)
            push!(waterbalance, record)
        end
    end

    # To retain all information, we need to save before and after callbacks that affect the
    # system, meaning we get multiple outputs on the same timestep. Make it configurable
    # to be able to disable callback saving as needed.
    # TODO: Check if regular saveat saving is before or after the callbacks.
    save_positions = Tuple(get(config, "save_positions", (true, true)))::Tuple{Bool, Bool}
    forcing_cb = PresetTimeCallback(datetime2unix.(used_time_uniq), update_forcings!;
                                    save_positions)
    allocation_cb = PeriodicCallback(allocate!, Δt; initial_affect = true, save_positions)
    Δt_output = Float64(get(config, "output_timestep", 86400.0))
    output_cb = PeriodicCallback(write_output!, Δt_output; initial_affect = true,
                                 save_positions = (false, false))

    callback = if run_modflow
        modflow_cb = PeriodicCallback(exchange_modflow!, Δt_modflow; initial_affect = true)
        CallbackSet(forcing_cb, allocation_cb, output_cb, modflow_cb)
    else
        CallbackSet(forcing_cb, allocation_cb, output_cb)
    end

    saveat = get(config, "saveat", [])
    integrator = init(prob,
                      AutoTsit5(Rosenbrock23());
                      progress = true,
                      progress_name = "Simulating",
                      callback,
                      saveat,
                      abstol = 1e-6,
                      reltol = 1e-3)

    return Register(integrator, param_hist, waterbalance)
end

function BMI.update(reg::Register)
    step!(reg.integrator)
    return reg
end

function BMI.update_until(reg::Register, time)
    integrator = reg.integrator
    t = integrator.t
    dt = time - t
    if dt < 0
        error("The model has already passed the given timestamp.")
    elseif dt == 0
        return reg
    else
        step!(integrator, dt)
    end
    return reg
end

BMI.get_current_time(reg::Register) = reg.integrator.t

run(config_file::AbstractString) = run(parsefile(config_file))

function run(config::AbstractDict)
    reg = BMI.initialize(Register, config)
    solve!(reg.integrator)
    if haskey(config, "waterbalance")
        path = config["waterbalance"]
        # create directory if needed
        mkpath(dirname(path))
        Arrow.write(path, reg.waterbalance)
    end
    return reg
end

function run()
    usage = "Usage: julia -e 'using Ribasim; Ribasim.run()' 'path/to/config.toml'"
    n = length(ARGS)
    if n != 1
        throw(ArgumentError(usage))
    end
    toml_path = only(ARGS)
    if !isfile(toml_path)
        throw(ArgumentError("File not found: $(toml_path)\n" * usage))
    end
    run(toml_path)
end
