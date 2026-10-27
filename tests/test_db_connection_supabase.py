import asyncio, asyncpg

async def main():
    # conn = await asyncpg.connect("postgresql://postgres:Southroserose.ng%2688@db.wqxloototgyjzrhdtmun.supabase.co:5432/postgres")
    conn = await asyncpg.connect("postgresql://postgres.wqxloototgyjzrhdtmun:Southroserose.ng%2688@aws-0-eu-west-1.pooler.supabase.com:5432/postgres")
    print(await conn.fetchval("select 1"))

asyncio.run(main())