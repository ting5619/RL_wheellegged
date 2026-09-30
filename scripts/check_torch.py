import json
from importlib.metadata import version
from pathlib import Path
import torch

assert torch.cuda.is_available(), 'CUDA is unavailable'
x = torch.randn(256, 256, device='cuda:0', requires_grad=True)
loss = (x @ x.T).square().mean()
loss.backward()
torch.cuda.synchronize()
assert torch.isfinite(loss) and torch.isfinite(x.grad).all()
result = {
    'torch': torch.__version__, 'cuda_runtime': torch.version.cuda,
    'gpu': torch.cuda.get_device_name(0),
    'vram_bytes': torch.cuda.get_device_properties(0).total_memory,
    'isaacsim': version('isaacsim'), 'isaaclab': version('isaaclab'),
    'rsl_rl': version('rsl-rl-lib'), 'cuda_forward_backward': 'PASS',
}
(Path(__file__).resolve().parents[1] / 'logs/torch-check.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
