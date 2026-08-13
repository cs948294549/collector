if __name__ == '__main__':
    import asyncio
    import time
    from Module.MAC import MACTable

    t = time.time()


    async def test():
        a = MACTable("172.21.64.18", "vdiannet", "cisco")
        res = await a.getMACTables()
        print(len(res))
        for i in res:
            print(i)


    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.close()

    print(time.time() - t)
