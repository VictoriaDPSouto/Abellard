# -*- coding: utf-8 -*-
"""Untitled48.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1u-jGwsi1xda8gcSmfdxsSEIiH56A17TT
"""

def rice_channel(N, kappa):

    h_los = (np.random.normal(0, 1, N) + 1j * np.random.normal(0, 1, N)) #np.exp(1j * (phi_0 + psi))
    h_nlos = (np.random.normal(0, 1, N) + 1j * np.random.normal(0, 1, N)) / np.sqrt(2)
    h_mk = np.sqrt(kappa / (kappa + 1)) * h_los + np.sqrt(1 / (kappa + 1)) * h_nlos

    return h_mk, h_los

#-----------------------------------------------------------------------------------------------------
def received_power(beta_mk, psi_mj, h_mk):
    return beta_mk * np.abs(np.dot(psi_mj, h_mk.conj()))**2

#-----------------------------------------------------------------------------------------------------
def energy_function(pb_positions, iot_positions, E_min, E_max, PT, N, frequency, alpha, kappa, tau):

    M = pb_positions.shape[0]
    K = iot_positions.shape[0]
    wavelength = speed_of_light / frequency

    # Ajustar as posições em z
    #iot_positions[:, 2] = iot_z  # Posição z dos dispositivos IoT (supondo que todos estão no plano z=0)
    pb_positions[:, 2] = PB_z  # Posição z dos PBs (altura fixa PB_z)

    # Distances between PBs and IoT devices
    distances = np.zeros((M, K))
    betas = np.zeros((M, K))

    # Canais
    H = np.zeros((M,K,N)).astype(complex)
    H_los = np.zeros((M,K,N)).astype(complex)
    psi_mj = np.zeros((M,K,N)).astype(complex)

    # GERAR OS CANAIS
    for m in range(M):
      for k in range(K):
        H[m][k][:], H_los[m][k][:]  = rice_channel(N, kappa)
        dx = pb_positions[m, 0] - iot_positions[k, 0]
        dy = pb_positions[m, 1] - iot_positions[k, 1]
        dz = pb_positions[m, 2]
        distances[m, k] = np.sqrt(dx**2 + dy**2 + dz**2)
        betas[m][k] = (wavelength**2) / ((16 * np.pi**2) * (distances[m][k]**alpha))

    # DETERMINAR A POTÊNCIA COLETADA

    for m in range(M):
      for k in range(K):
          for n in range(N):
            psi_mj[m][k][n] = np.sqrt(PT / N) * (H[m][k][n]/np.abs(H[m][k][n])) # <----- ALTERAR ENTRE H E HLOS AQUI

      P_k_array = np.zeros((K,K))
      P_k_array_real = np.zeros((K,K))

      for k in range(K):
        for j in range(K):
          P_k_array[k][j] = received_power(betas[m][j], psi_mj[m][k], H[m][j]) # <------ ALTERAR ENTRE H E HLOS AQUII
          P_k_array_real[k][j] = received_power(betas[m][j], psi_mj[m][k], H[m][j])

      P_k_array += P_k_array;
      P_k_array_real += P_k_array_real;

    # DETERMINAR A ENERGIA COLETADA
    E_collected = np.zeros((K,K))
    E_device = np.zeros(K)

    E_collected_real = np.zeros((K,K))
    E_device_real = np.zeros(K)

    for k in range(K):
        for j in range(K):
          E_collected[k][j] = tau*((mu / (1 + np.exp(-a * (P_k_array[k][j] - b)))) - (mu * Omega)) / (1 - Omega)
          E_collected_real[k][j] = tau*((mu / (1 + np.exp(-a * (P_k_array_real[k][j] - b)))) - (mu * Omega)) / (1 - Omega)

    E_device = np.sum(E_collected, axis = 0)
    E_device_real = np.sum(E_collected_real, axis = 0)

    return E_device, E_device_real

#-------------------------------------------------------------------------------------------------------

def fitness_function(pb_positions, iot_positions, E_min, E_max, PT, N, tau_k, frequency, alpha):
    # Chamar a energy_function para obter a energia coletada por dispositivo
    collected_energies, collected_energies_real = energy_function(pb_positions, iot_positions, E_min, E_max, PT, N, frequency, alpha, kappa, tau)

    penalty = 0  # Inicialização da penalidade

    collected_fitness = collected_energies

    # Verificação de penalidades caso a energia coletada esteja abaixo do mínimo exigido
    for k in range(len(collected_fitness)):
        if collected_fitness[k] < E_min[k]:
            penalty += np.abs(collected_fitness[k] - E_min[k])

        if collected_fitness[k] > E_max[k]:
            collected_fitness[k] = E_max[k]

    # Cálculo do fitness final, penalizando se a energia mínima não for atendida
    fitness = np.sum(collected_fitness) - penalty

    return fitness * 1e06, collected_energies, collected_energies_real


#-------------------------------------------------------------------------------------------------
import numpy as np


PT = 2  # Total transmission power for each PB
frequency = 915e6  # Frequency in Hz
speed_of_light = 3e8  # Speed of light in m/s
alpha = 2.5  # Path loss exponent
mu = 10.73e-3  # Maximum power that can be collected in Watts
b = 0.2308  # Constant in the logistic function for energy conversion
a = 5.365  # Constant in the logistic function for energy conversion
Omega = 1 / (1 + np.exp(a * b))  # Constant related to the zero-input/zero-output response

def particle_swarm_optimization_linear(swarm_size, num_pbs, bounds, max_iterations, pb_positions, iot_positions, E_min, E_max, PT, N, tau_k, frequency, alpha, R, N_realizacao):

    total_energy = np.zeros(N_realizacao)
    total_real_energy = np.zeros(N_realizacao)
    convergencia = np.zeros((N_realizacao, max_iterations))

    # Iteração para várias realizações de canal
    for realization in range(N_realizacao):

        # Inicialização do enxame
        swarm_positions = np.tile(pb_positions, (swarm_size, 1, 1))
        swarm_velocities = 0.5 * (np.random.uniform(-R, R, (swarm_size, num_pbs, 3)))
        swarm_positions[:, :, 2] = pb_positions[:, 2]

        swarm_personal_best_positions = np.copy(swarm_positions)

        fitness_results = [
            fitness_function(p, iot_positions, E_min, E_max, PT, N, tau_k, frequency, alpha) for p in swarm_positions
        ]

        swarm_personal_best_scores = np.array([result[0] for result in fitness_results])
        swarm_personal_best_collected_energies = np.array([result[1] for result in fitness_results])
        swarm_personal_best_collected_energies_real = np.array([result[1] for result in fitness_results])

        # Melhor posição global inicial
        global_best_position = np.copy(swarm_personal_best_positions[np.argmax(swarm_personal_best_scores)])
        global_best_score = np.max(swarm_personal_best_scores)
        global_best_collected_energies = swarm_personal_best_collected_energies[np.argmax(swarm_personal_best_scores)]
        global_best_collected_energies_real = swarm_personal_best_collected_energies_real[np.argmax(swarm_personal_best_scores)]


        fitness_history = []

        # Otimização PSO
        for iteration in range(max_iterations):

            inertia = 0.9 - (0.5 * iteration / max_iterations)
            r1, r2 = np.random.rand(2)

            for i in range(swarm_size):
                # Atualização das velocidades
                swarm_velocities[i] = (
                    inertia * swarm_velocities[i] +
                    2 * r1 * (swarm_personal_best_positions[i] - swarm_positions[i]) +
                    1.7 * r2 * (global_best_position - swarm_positions[i])
                )
                swarm_velocities[i] = np.clip(swarm_velocities[i], -R / 2, R / 2)

                # Atualização das posições
                new_position = swarm_positions[i] + swarm_velocities[i]
                new_position = np.clip(new_position, bounds[0], bounds[1])
                new_position[:, 2] = pb_positions[:, 2]
                swarm_positions[i] = new_position

                # Avaliação da nova posição
                current_fitness, current_collected_energies, current_collected_energies_real = fitness_function(
                    swarm_positions[i], iot_positions, E_min, E_max, PT, N, tau_k, frequency, alpha
                )

                # Atualização do best pessoal
                if current_fitness > swarm_personal_best_scores[i]:
                    swarm_personal_best_scores[i] = current_fitness
                    swarm_personal_best_positions[i] = np.copy(swarm_positions[i])
                    swarm_personal_best_collected_energies[i] = current_collected_energies
                    swarm_personal_best_collected_energies_real[i] = current_collected_energies_real

            # Atualização do best global
            #for i in range(swarm_size):
                if swarm_personal_best_scores[i] > global_best_score:
                    global_best_score = swarm_personal_best_scores[i]
                    global_best_position = np.copy(swarm_personal_best_positions[i])
                    global_best_collected_energies = swarm_personal_best_collected_energies[i]
                    global_best_collected_energies_real = swarm_personal_best_collected_energies_real[i]
            fitness_history.append(global_best_score)

            count_real = np.sum(global_best_collected_energies_real > E_min)

        convergencia[realization][:] = fitness_history[:]

        # Acumula resultados desta realização
        total_energy[realization] = np.sum(global_best_collected_energies)
        total_real_energy[realization] = np.sum(global_best_collected_energies_real)

         # Média do contador de dispositivos com energia coletada > E_min
        mean_count_real = np.mean(count_real)


    # Calcula médias ao final de todas as realizações
    mean_energy = np.mean(total_energy)
    mean_real_energy = np.mean(total_real_energy)

    return global_best_position, global_best_score, mean_energy, mean_real_energy, mean_count_real



np.random.seed(10)

# Parâmetros globais usados por todos os códigos
PT = 2  # Total transmission power for each PB
frequency = 915e6  # Frequency in Hz
speed_of_light = 3e8  # Speed of light in m/s
alpha = 2.5  # Path loss exponent
mu = 10.73e-3  # Maximum power that can be collected in Watts
kappa = 1
b = 0.2308  # Constant in the logistic function for energy conversion
a = 5.365  # Constant in the logistic function for energy conversion
Omega = 1 / (1 + np.exp(a * b))  # Constant related to the zero-input/zero-output response

num_pbs = M = 4  # Number of PBs
iot_z = 0;
PB_z = 2;
tau = 1;
swarm_size = 20
max_iterations = 500
n_realizacao = 100
N_set = 10

N = 4 # Antennas per PB

# Listas para armazenar os resultados

R = 40
pso_data = []
pso_e=0
pso_e_r=0
cou=0

#iot_positions_aux = np.zeros((N_set, 50, 3))

iot_positions_aux = np.loadtxt("all_iot_positions.csv", delimiter=",")

K_set = 50;
cont = 0;
x_iot = np.zeros((10, K_set))
y_iot = np.zeros((10, K_set))
for j in range(0, 500, K_set):
  cont1 = 0;
  for kk in range(j,j+K_set,1):
    x_iot[cont][cont1] = iot_positions_aux[kk][0]
    y_iot[cont][cont1] = iot_positions_aux[kk][1]
    cont1 += 1;
  cont += 1;



#iot_positions_aux = np.random.uniform(0, R, (N_set, 50, 3))

import time
inicio = time.time()

for K in range (20,21,10):

    Energia_Real_Solucao = np.zeros((K,R))
    teste_energy = np.zeros(N_set)
    teste_energy_n = np.zeros(N_set)
    co_real = np.zeros(N_set)



    for dev in range(N_set):
      #print(K, R)
      print(dev)
      random_energies_real = []
      pso_energies_real = []

      # Geração de parâmetros
      E_min_benchmark = np.random.uniform(6e-6, 6e-6, K)
      E_max_benchmark = np.random.uniform(6e-6, 6e-6, K)

      # Geração de posições

      iot_positions_new = np.hstack((x_iot[dev][0:K].reshape(K,1), y_iot[dev][0:K].reshape(K,1)))
      pb_positions = np.random.uniform(0, R, (num_pbs, 3))

      pb_positions[:, 2] = PB_z
      #iot_positions[:, 2] = iot_z

      nova_coluna = np.ones((iot_positions_new.shape[0], iot_z))
      iot_positions = np.hstack((iot_positions_new, nova_coluna))

      # Execução do método PSO
      _, _, pso_energies, pso_energy_real,c_real = particle_swarm_optimization_linear(
          swarm_size, num_pbs, (0, R), max_iterations, pb_positions, iot_positions,
          E_min_benchmark[:K], E_max_benchmark[:K], PT, N, tau, frequency, alpha, R, n_realizacao
      )

      teste_energy[dev] =  pso_energy_real;
      teste_energy_n[dev] =  pso_energies;
      co_real[dev] = c_real;
    pso_e=np.mean(teste_energy)
    pso_e_r=np.mean(teste_energy_n)
    cou=np.mean(co_real)
    pso_data.append([K, R,N, np.mean(teste_energy), np.mean(teste_energy_n), np.mean(co_real)])
    print("PSO - Mean energy of all devices real:",pso_e)
    print("PSO - Mean energesy of all device:",pso_e_r)
    print("PSO - Mean energy of all devices with E > E_min:",cou)



# RANDOM
random_data = []
r_e=0
r_e_r=0
coun=0
n_realizacao = 1000
for K in range(20, 21, 10):
    print(K)
    E_final = np.zeros(n_realizacao)
    E_final_no = np.zeros(n_realizacao)
    N_dispositivos_real = np.zeros(n_realizacao)

    for r in range(n_realizacao):
        E_final_real = np.zeros(N_set)
        E_final_n = np.zeros(N_set)

        for dev in range(N_set):
            maior_qtd_devices = K
            E_min_benchmark = np.random.uniform(6e-6, 6e-6, maior_qtd_devices)
            E_max_benchmark = np.random.uniform(6e-6, 6e-6, maior_qtd_devices)

            # Geração de posições
            pb_positions = np.random.uniform(0, R, (num_pbs, 3))
            #iot_positions = np.random.uniform(0, R, (K, 3))
            #iot_positions = iot_positions_aux[dev,0:K,:]
            pb_positions[:, 2] = PB_z
            #iot_positions[:, 2] = iot_z

            iot_positions_new = np.hstack((x_iot[dev][0:K].reshape(K,1), y_iot[dev][0:K].reshape(K,1)))

            nova_coluna = np.ones((iot_positions_new.shape[0], iot_z))
            iot_positions = np.hstack((iot_positions_new, nova_coluna))

            # Execução do método Random
            random_energy, random_energy_real = energy_function(
                pb_positions, iot_positions, E_min_benchmark[:K], E_max_benchmark[:K],
                PT, N, frequency, alpha, kappa, tau
            )

            E_final_real[dev] = np.sum(random_energy_real)
            E_final_n[dev] = np.sum(random_energy)
            cont_real = 0
            for k in range(K):
                if random_energy_real[k] > E_min_benchmark[k]:
                    cont_real += 1

        N_dispositivos_real[r] = cont_real
        E_final[r] = np.mean(E_final_real)
        E_final_no[r] = np.mean(E_final_n)
    r_e=np.mean(E_final)
    r_e_r=np.mean(E_final_no)
    coun=np.mean(N_dispositivos_real)
    random_data.append([K, R,N, np.mean(E_final), np.mean(E_final_no), np.mean(N_dispositivos_real)])
    print("RANDOM - Mean energy of all devices real:",r_e)
    print("RANDOM - Mean energesy of all device:",r_e_r)
    print("RANDOM - Mean energy of all devices with E > E_min:",coun)

fim = time.time()
print(fim - inicio)

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

pso_df = pd.DataFrame(pso_data, columns=['K', 'R',"N", 'Energia_Real_PSO', 'Energia_No_Shadowing_PSO', 'Dispositivos_Atendidos_PSO'])
random_df = pd.DataFrame(random_data, columns=['K', 'R',"N", 'Energia_Real_Aleatorio', 'Energia_No_Shadowing_Aleatorio', 'Dispositivos_Atendidos_Aleatorio'])
pso_df.to_csv('resultados_pso_kc.csv', index=False)
random_df.to_csv('resultados_aleatorio_kc.csv', index=False)