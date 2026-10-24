-- Read-only smoke test: run on the router with `lua smoke.lua [LUA_LIBRARY_ROOT]`.
-- The optional root permits testing an unpacked package without installing it.
if arg[1] then
	package.path = arg[1] .. '/?.lua;' .. arg[1] .. '/?/init.lua;' .. package.path
end

local client = require('luci.model.docker').new()
assert(client.options.version == 'v1.40', 'Unexpected Docker API version')

local function check(name, response)
	assert(response and response.code == 200,
		name .. ': HTTP ' .. tostring(response and response.code))
	assert(type(response.body) == 'table', name .. ': missing JSON response')
	print(name .. ': OK')
	return response.body
end

local version = check('version', client:version())
assert(version.Version, 'Docker version is missing')
print('Docker Engine: ' .. version.Version)
check('info', client:info())
check('containers', client.containers:list({query = {all = true}}))
check('images', client.images:list({query = {all = true}}))
check('networks', client.networks:list())
check('volumes', client.volumes:list())
check('disk usage', client:df())

-- Exercise actual Lua menu registration without a running LuCI HTTP session.
local routes = {}
function entry(path, action, title, order)
	local result = {action = action, title = title, order = order}
	routes[table.concat(path, '/')] = result
	return result
end
function firstchild() return 'firstchild' end
function cbi(path) return path end
function form(path) return path end
function call(name) return name end
function _(text) return text end

require('luci.controller.dockerman').index()
assert(routes['admin/docker'].title == 'Docker', 'Top-level Docker menu is missing')
for _, name in ipairs({'config', 'overview', 'containers', 'images', 'networks', 'volumes', 'events'}) do
	assert(routes['admin/docker/' .. name], 'Missing Docker page: ' .. name)
end
assert(not routes['admin/services/dockerman'], 'Dockerman JS menu is still registered')
print('Lua Dockerman menu and read-only Docker API checks passed')
