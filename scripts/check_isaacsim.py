import json
from pathlib import Path
from isaacsim import SimulationApp

app = SimulationApp({'headless': True, 'width': 640, 'height': 480,
                     'multi_gpu': False, 'limit_cpu_threads': 4})
try:
    for _ in range(10):
        app.update()
    assert app.is_running(), 'Isaac Sim application stopped unexpectedly'
    result = {'test': 'isaacsim_headless_startup', 'updates': 10, 'status': 'PASS'}
    (Path(__file__).resolve().parents[1] / 'logs/isaacsim-check.json').write_text(json.dumps(result, indent=2)+'\n')
    print('ISAACSIM_STARTUP_PASS', json.dumps(result), flush=True)
finally:
    app.close()
