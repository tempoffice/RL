# python3
# Author: Scc_hy
# Create Date: 2023-01-25
# Func: DDPG
# ============================================================================
import typing as typ
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.nn import functional as F
from ._base_net import DDPGValueNet as valueNet
from ._base_net import DDPGPolicyNet as policyNet
import copy




class DDPG:
    def __init__(self, 
                state_dim: int, 
                actor_hidden_layers_dim: typ.List, 
                critic_hidden_layers_dim: typ.List, 
                action_dim: int,
                actor_lr: float,
                critic_lr: float,
                gamma: float,
                DDPG_kwargs: typ.Dict,
                device: torch.device
                ):
        self.actor = policyNet(state_dim, actor_hidden_layers_dim, action_dim, action_bound = DDPG_kwargs['action_bound'])
        self.critic = valueNet(state_dim + action_dim, critic_hidden_layers_dim)
        self.target_actor = copy.deepcopy(self.actor)
        self.target_critic = copy.deepcopy(self.critic)

        self.actor.to(device)
        self.critic.to(device)
        self.target_actor.to(device)
        self.target_critic.to(device)
        self.actor_opt = torch.optim.Adam(self.actor.parameters(), lr=actor_lr)
        self.critic_opt = torch.optim.Adam(self.critic.parameters(), lr=critic_lr)
        
        self.gamma = gamma
        self.device = device
        self.count = 0
        # soft update parameters
        self.tau = DDPG_kwargs.get('tau', 0.8)
        self.action_dim = action_dim
        # Normal sigma
        self.sigma = DDPG_kwargs.get('sigma', 0.1)

    def policy(self, state):
        state = torch.FloatTensor([state]).to(self.device)
        act = self.actor(state)
        return act.detach().numpy()[0] + self.sigma * np.random.rand(self.action_dim)

    def soft_update(self, net, target_net):
        for param_target, param in zip(target_net.parameters(), net.parameters()):
            param_target.data.copy_(
                param_target.data * (1 - self.tau) + param.data * self.tau
            )

    def update(self, samples):
        self.count += 1
        state, action, reward, next_state, done = zip(*samples)
        state = torch.FloatTensor(state).to(self.device)
        action = torch.tensor(action).to(self.device)
        reward = torch.tensor(reward).view(-1, 1).to(self.device)
        reward = (reward + 10.0) / 10.0  # 对奖励进行修改,方便训练
        next_state = torch.FloatTensor(next_state).to(self.device)
        done = torch.FloatTensor(done).view(-1, 1).to(self.device)
        
        target_action = self.target_actor(state)
        next_q_value = self.target_critic(next_state, target_action)
        q_targets = reward + self.gamma * next_q_value * ( 1.0 - done )
        critic_loss = torch.mean(F.mse_loss(self.critic(state, action).float(), q_targets.float()))
        self.critic_opt.zero_grad()
        critic_loss.backward()
        self.critic_opt.step()
        
        # 计算采样的策略梯度，以此更新当前 Actor 网络
        ac_action = self.actor(state)
        actor_loss = -torch.mean(self.critic(state, ac_action))
        self.actor_opt.zero_grad()
        actor_loss.backward()
        self.actor_opt.step()
        
        self.soft_update(self.actor, self.target_actor)
        self.soft_update(self.critic, self.target_critic)
