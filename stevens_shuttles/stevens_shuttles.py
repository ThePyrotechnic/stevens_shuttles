import ShuttleService

if __name__ == '__main__':
    ss = ShuttleService.ShuttleService(307)
    red_line = [r for r in ss.get_routes() if r['long_name'] == 'Gray Line North Loop'][0]
    red_line_stop_ids = ss.get_stop_ids_for_route(red_line['id'])
    red_line_stops = [s for s in ss.get_stops() if s['id'] in red_line_stop_ids]
    red_line_shuttles = [s for s in ss.get_vehicle_statuses() if s['route_id'] == red_line['id']]
    print(red_line_shuttles)
