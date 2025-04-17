# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.6
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
import sys
sys.path.append('../../../../..')
sys.path.append('/usr/local/lib/wingpro10/')

import wingdbstub
wingdbstub.Ensure()

import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from typing import List
from chaski.node import ChaskiNode
import seaborn as sns

from chaski.node import ChaskiNode
from chaski.utils import viz

from string import ascii_uppercase
import random
import asyncio
import time

# %%
topics = list(ascii_uppercase)[:4]
topics

root = ChaskiNode(
    name='Root',
    root=True,
)

nodes = [root]
root

# %%
for i in range(50):
    node = ChaskiNode(
        name=f'N{str(i+1).rjust(2, "0")}',
        subscriptions=[random.choice(topics) for _ in range(1)],
        paired=False,
        max_connections = 5,
        )
    nodes.append(node)
    await node.connect(root, discovery=True, discovery_timeout=0.3)

# %%
viz.display_subscriptions_graph(nodes)

# %%

# %%

# %%


