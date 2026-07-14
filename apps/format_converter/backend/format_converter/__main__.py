"""format_converter 入口：启动 FastAPI 服务。"""

import uvicorn


def main():
    uvicorn.run(
        "format_converter.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
