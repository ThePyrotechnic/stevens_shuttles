import ShuttleService

if __name__ == '__main__':
    # TODO
    # 1. List routes
    # 2. Get desired routes
    # 3. Get stops for routes
    # 4. Get geo-fence for routes
    # 5. Check shuttle position against manual schedule and geo-fences

    ss = ShuttleService.ShuttleService(307)
    red_line = [r for r in ss.get_routes() if r['short_name'] == 'RL'][0]
    red_line_stop_ids = ss.get_stop_ids_for_route(red_line['id'])
    red_line_stops = [s for s in ss.get_stops() if s['id'] in red_line_stop_ids]
    print(red_line_stops)
