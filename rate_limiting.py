import json
import time
import redis

def get_identifiers():
    ret = ['ip:' + request.remote_addr]
    if g.user.is_authenticated():
        ret.append('user:' + g.user.get_id())
    return ret

def sliding_window(conn, base_keys, minute=0, hour=0, day=0, weight=1):
    limits = [minute, hour, day, weight, int(time.time())]
    return bool(sliding_window_lua(conn, keys=base_keys, args=limits))

def _script_load(script):
    sha = [None]
    def call(conn, keys=[], args=[], force_eval=False):
        if not force_eval:
            if not sha[0]:
                sha[0] = conn.execute_command(
                    "SCRIPT", "LOAD", script, parse="LOAD")
            try:
                return conn.execute_command(
                    "EVALSHA", sha[0], len(keys), *(keys+args))
            except redis.exceptions.ResponseError as msg:
                if not msg.args[0].startswith("NOSCRIPT"):
                    raise
        return conn.execute_command(
            "EVAL", script, len(keys), *(keys+args))
    return call

sliding_window_lua = _script_load('''
local slice = {60, 3600, 86400}
local precision = {1, 60, 1800}
local dkeys = {'m', 'h', 'd'}
local ts = tonumber(table.remove(ARGV))
local weight = tonumber(table.remove(ARGV))
local fail = false

for _, ready in ipairs({false, true}) do

    for i = 1, math.min(#ARGV, #slice) do
        local limit = tonumber(ARGV[i])

        if limit > 0 then

            local cutoff = ts - slice[i]
            local curr = '' .. (precision[i] * math.floor(ts / precision[i]))
            local suff = ':' .. dkeys[i]
            local suff2 = suff .. ':l'

            for j, k in ipairs(KEYS) do
                local key = k .. suff
                local key2 = k .. suff2
                if ready then
                    -- if we get here, our limits are fine
                    redis.call('incrby', key, weight)
                    local oldest = redis.call('lrange', key2, '0', '1')
                    if oldest[2] == curr then
                        redis.call('ltrim', key2, 0, -3)
                        redis.call('rpush', key2, weight + tonumber(oldest[1]), oldest[2])
                    else
                        redis.call('rpush', key2, weight, curr)
                    end
                    redis.call('expire', key, slice[i])
                    redis.call('expire', key2, slice[i])
                else

                    local total = tonumber(redis.call('get', key) or '0')

                    while total + weight > limit do
                        local oldest = redis.call('lrange', key2, '0', '1')
                        if #oldest == 0 then
                            break
                        end
                        if tonumber(oldest[2]) <= cutoff then
                            total = tonumber(redis.call('incrby', key, -tonumber(oldest[1])))
                            redis.call('ltrim', key2, '2', '-1')
                        else
                            break
                        end
                    end
                    fail = fail or total + weight > limit
                end
            end
        end
    end
    if fail then
        break
    end
end
return fail
''')

def test(count=10000):
    import uuid
    keys = [str(uuid.uuid4())]
    c = redis.Redis(host='redis', port=6379)

    t = time.time()
    for i in range(count):
        sliding_window(c, keys, 10000, 20000)
    print ("API Rate Limiter Performance:", count / (time.time() - t))

if __name__ == '__main__':
    test()
