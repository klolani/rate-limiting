# rate-limiting

## Test Rate Limiter

Vary the count in the test function and note the Rate Limiter performance with the varying counts

```
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
```
