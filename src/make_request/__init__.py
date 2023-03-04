import httpx

async_client = httpx.AsyncClient(http2=True, limits=httpx.Limits(max_connections=100, max_keepalive_connections=20))


async def send_request(api_url: str, headers: dict[str, str | int], method: str = 'get',
                       data: str | None = None):
    try:
        if method.lower() == "get":
            response = await async_client.get(url=api_url, headers=headers, timeout=360000)
        elif method.lower() == "post":
            if data:
                response = await async_client.post(url=api_url, json=data, headers=headers, timeout=360000)
            else:
                response = await async_client.post(url=api_url, headers=headers, timeout=360000)
        else:
            return None
    except httpx.HTTPError as http_err:
        raise http_err
    except Exception as err:
        raise err
    return response.json()
