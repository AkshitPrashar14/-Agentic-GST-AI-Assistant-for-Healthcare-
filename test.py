"""Test script for CUDA availability."""
import torch
print(torch.cuda.get_device_name(0))
print(torch.cuda.memory_allocated() / 1e9, "GB")
