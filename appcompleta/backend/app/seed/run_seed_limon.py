import asyncio
import json

from app.database import AsyncSessionLocal
from app.seed.seed_limon import seed_limon_data
from app.seed.validate_limon_bi import validate_limon_bi


async def main():
    async with AsyncSessionLocal() as db:
        await seed_limon_data(db, force=True)
        await db.commit()
        summary = await validate_limon_bi(db)
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
