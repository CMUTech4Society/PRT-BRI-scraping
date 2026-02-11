#!/usr/bin/env python3
import time
import json
import os
from argparse import ArgumentParser

import requests

# HTTP Header Values
headers = {
    'Content-Type': 'application/json;charset=UTF-8',
    'X-PowerBI-ResourceKey': 'd2b08558-c2e1-4763-a0a5-376485fd1dee',
    'Origin': 'https://app.powerbi.com',
}
params = {
    'synchronous': 'true',
}

def parse():
    parser = ArgumentParser()
    parser.add_argument("--export", required=True,
                        help="path to the export directory")
    parser.add_argument("--request-body", required=True,
                        help="json file to use as request body")
    parser.add_argument("--routes", required=True,
                        help="newline-separated file of route names")
    parsed = parser.parse_args()

    return parsed.export, parsed.request_body, parsed.routes

def make_export_path(export_path):
    if not os.path.exists(export_path):
        os.mkdir(export_path, mode=0o700)
    if os.path.isfile(export_path):
        raise FileExistsError(f'Directory "{export_path}" is a file.')

    return export_path

def get_requests_body(request_body_path):
    with open(request_body_path, 'r') as f:
        json_data = json.load(f)

    json_route_dict = json_data['queries'][0]['Query']['Commands'][0] \
                               ['SemanticQueryDataShapeCommand']['Query']['Where'] \
                               [0]['Condition']['In']['Values'][0][0]['Literal']
    return json_data, json_route_dict

def get_routes(route_path):
    # List of routes
    routes = []
    with open(route_path, 'r') as f:
        for line in f:
            routes.append(line.strip())
    return routes

def main(export_path, request_body_path, route_path):
    export_path = make_export_path(export_path)
    json_data, json_route_dict = get_requests_body(request_body_path)
    routes = get_routes(route_path)

    for route in routes:
        json_route_dict['Value'] = "'" + route + "'"

        timestr = time.strftime("%Y_%m_%d-%H_%M")
        print(export_path, route, timestr)
        filepath = os.path.join(export_path, route + '_' + timestr + '.json')
        with open(filepath, 'x') as file:
            response = requests.post(
                'https://wabi-us-east-a-primary-api.analysis.windows.net/public/reports/querydata',
                params=params,
                headers=headers,
                json=json_data,
            )
            file.write(response.text)
        print(response.text)
        print(filepath)
        time.sleep(0.5)

if __name__ == '__main__':
    export_path, request_body_path, route_path = parse()
    main(export_path, request_body_path, route_path)
