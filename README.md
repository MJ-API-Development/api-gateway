# EOD STOCK API - API--GATEWAY-VERSION 0.0.1

**api-gateway** is a Python-based API Gateway built using the FastAPI framework. It provides several key features to 
secure and manage your API endpoints.

## Features

### API key based authorization

API key based authorization ensures that only authorized clients can access your API endpoints. 
When a client sends a request to the API gateway, it checks the API key provided in the request headers and 
verifies it against a list of authorized API keys.

### Regional edge server based request throttling

The regional edge server based request throttling feature ensures that a client cannot overwhelm the API gateway 
with too many requests. 

The API gateway keeps track of the number of requests coming from each edge IP address and enforces a limit on the 
number of requests that can be made in a given time period. if the limit is exceeded the requests will be throttled 
this will not affect other clients making use of our services from regions where there is no huge traffic

### API key based client request rate limiting

API key based client request rate limiting provides an additional layer of protection against DDoS attacks by limiting 
the number of requests a client can make in a given time period. 

The API Gateway checks the number of requests made by each client using their API key and enforces a limit on the 
number of requests that can be made in a given time period.


### Regex based request filtering

Regex based request filtering ensures that only whitelisted requests can reach the API gateway. The API gateway checks 
the request URL against a list of regular expressions and rejects any requests that do not match any of the 
regular expressions. The regular expressions matches pre configured url routes


### Resource based request authorization

Resource based request authorization allows you to control which API resources can be accessed by each client. 
The API gateway checks the API key or username provided in the request headers and verifies it against a 
list of authorized clients for the specific resource.

## Getting started

To get started with **api-gateway**, follow these steps:

1. Clone the repository:
https://github.com/MJ-API-Development/api-gateway

The API gateway should now be accessible at `https://gateway.eod-stock-api.site`.

## Contributing

If you want to contribute to **api-gateway**, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix:


3. Make your changes and commit them:

4. Push your changes to your fork:

5. Create a pull request to the main repository.

## License

**api-gateway** is licensed under the MIT License. See the `LICENSE` file for details. 
