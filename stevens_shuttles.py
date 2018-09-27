import ShuttleService

if __name__ == '__main__':
    ss = ShuttleService.ShuttleService(307)
    red_line = [r for r in ss.get_routes() if r.short_name == 'RL'][0]
    pass
