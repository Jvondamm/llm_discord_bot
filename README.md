Install the package with

```commandline

```

If you get 'Torch not compiled with CUDA enabled'
then navigate to https://pytorch.org/get-started/locally/ and select the correct options for your system (run nvcc --version) to figure out your CUDA version,
then run the pip install command that is generated.
After the installation, do

import torch
torch.cuda.is_available()
 to verify the installation