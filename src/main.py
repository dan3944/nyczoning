import asyncio
import config
import download
import notify


async def main():
    args = config.parse_args()
    await download.main()
    await notify.notify_meetings(args)

if __name__ == '__main__':
    asyncio.run(main())
