#!/usr/bin/env python
#
# Copyright 2019 the original author or authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# TODO: Add user interaction:
# TODO:   - Selecting circuit node with mouse
# TODO:   - Same gate twice erases (e.g. pressing X key already on an X gate erases it)
# TODO:     - If gate was rotated, make unrotated (e.g. pressing X on rotated X gate makes X)
# TODO: Use NUM_STATE_DIMS everywhere
# TODO: Make TSP and other demos, including chemistry
# TODO: Make displays update during optimization
# TODO: Modify optimizer to fit pluggable Aqua framework
# TODO: Create network graph component?
# TODO: Update QSphere visualization and leverage it here
#
"""Demonstrate Variational Quantum Eigensolver (VQE) concepts using Qiskit and Pygame"""

import pygame
import numpy as np

WINDOW_SIZE = 1660, 1000


import random
import scipy.optimize
from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister
from qiskit import execute
from qiskit_aqua.translators.ising import maxcut
from pygame.locals import *
from model.circuit_grid_model import *
from model import circuit_node_types as node_types
from containers.hbox import HBox
from containers.vbox import VBox
from utils.colors import *
from utils.states import NUM_QUBITS, NUM_STATE_DIMS
from utils.navigation import *
from utils.gamepad import *
from viz.circuit_diagram import CircuitDiagram
from viz.expectation_grid import ExpectationGrid
from viz.network_graph import NetworkGraph
from controls.circuit_grid import *


class VQEPlayground():
    """Main object for application"""
    def __init__(self):
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        self.background = pygame.Surface(self.screen.get_size())
        self.circuit_grid_model = None
        self.circuit_grid = None
        self.top_sprites = None
        self.right_sprites = None
        self.expectation_grid = None
        self.network_graph = None

    def main(self):
        if not pygame.font: print('Warning, fonts disabled')
        if not pygame.mixer: print('Warning, sound disabled')

        pygame.init()

        pygame.joystick.init()
        num_joysticks = pygame.joystick.get_count()

        joystick = False
        if num_joysticks > 0:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()

        self.background = pygame.Surface(self.screen.get_size())
        self.background = self.background.convert()
        self.background.fill(WHITE)

        pygame.font.init()

        self.circuit_grid_model = CircuitGridModel(NUM_QUBITS, 18)

        pygame.display.set_caption('VQE Playground')

        self.screen.blit(self.background, (0, 0))
        pygame.display.flip()

        # Prepare objects
        clock = pygame.time.Clock()

        self.circuit_grid_model.set_node(0, 0, CircuitGridNode(node_types.Y))
        self.circuit_grid_model.set_node(1, 0, CircuitGridNode(node_types.Y))
        self.circuit_grid_model.set_node(2, 0, CircuitGridNode(node_types.Y))
        self.circuit_grid_model.set_node(3, 0, CircuitGridNode(node_types.Y))
        self.circuit_grid_model.set_node(4, 0, CircuitGridNode(node_types.Y))
        self.circuit_grid_model.set_node(5, 0, CircuitGridNode(node_types.Y))

        self.circuit_grid_model.set_node(1, 1, CircuitGridNode(node_types.X, 0, 0))
        self.circuit_grid_model.set_node(2, 2, CircuitGridNode(node_types.X, 0, 1))
        self.circuit_grid_model.set_node(3, 3, CircuitGridNode(node_types.X, 0, 2))
        self.circuit_grid_model.set_node(4, 4, CircuitGridNode(node_types.X, 0, 3))
        self.circuit_grid_model.set_node(5, 5, CircuitGridNode(node_types.X, 0, 4))

        # circuit_grid_model.set_node(0, 3, CircuitGridNode(node_types.X))
        # circuit_grid_model.set_node(1, 3, CircuitGridNode(node_types.Y))
        # circuit_grid_model.set_node(2, 3, CircuitGridNode(node_types.Y))
        # circuit_grid_model.set_node(3, 3, CircuitGridNode(node_types.Y))

        circuit = self.circuit_grid_model.compute_circuit()

        adj_matrix = np.array([
            [0.0, 1.0, 0.0, 1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
            [1.0, 0.0, 1.0, 0.0, 1.0, 1.0],
            [0.0, 1.0, 1.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.0, 1.0, 0.0]
        ])

        # adj_matrix = np.array([
        #     [0.0, 1.0, 0.0, 1.0],
        #     [1.0, 0.0, 1.0, 0.0],
        #     [0.0, 1.0, 0.0, 1.0],
        #     [1.0, 0.0, 1.0, 0.0]
        # ])

        # adj_matrix = np.array([
        #     [0.0, 1.0, 1.0, 1.0],
        #     [1.0, 0.0, 1.0, 0.0],
        #     [1.0, 1.0, 0.0, 1.0],
        #     [1.0, 0.0, 1.0, 0.0]
        # ])

        # adj_matrix = np.array([
        #     [0.0, 1.0, 1.0, 1.0],
        #     [1.0, 0.0, 1.0, 1.0],
        #     [1.0, 1.0, 0.0, 1.0],
        #     [1.0, 1.0, 1.0, 0.0]
        # ])

        maxcut_op, maxcut_shift = maxcut.get_maxcut_qubitops(adj_matrix)

        # TODO: Find different approach of calculating and retrieving diagonal
        maxcut_op._paulis_to_matrix()
        eigenvectors = maxcut_op._dia_matrix

        self.expectation_grid = ExpectationGrid(circuit, eigenvectors)

        self.network_graph = NetworkGraph(adj_matrix)

        # TODO: Put this flag in expectation_grid, making methods to
        # TODO:     update respective matrices?
        expectation_value_dirty = True

        self.top_sprites = HBox(500, 0, self.network_graph)
        self.right_sprites = VBox(1400, 0, self.expectation_grid)

        self.circuit_grid = CircuitGrid(10, 500, self.circuit_grid_model)
        self.screen.blit(self.background, (0, 0))

        self.top_sprites.draw(self.screen)
        self.right_sprites.draw(self.screen)
        self.circuit_grid.draw(self.screen)
        pygame.display.flip()

        gamepad_repeat_delay = 100
        gamepad_neutral = True
        gamepad_pressed_timer = 0
        gamepad_last_update = pygame.time.get_ticks()

        bit_str_meas = '0000'


        # Main Loop
        going = True
        while going:
            clock.tick(30)

            pygame.time.wait(10)

            if joystick:
                gamepad_move = False
                joystick_hat = joystick.get_hat(0)

                if joystick_hat == (0, 0):
                    gamepad_neutral = True
                    gamepad_pressed_timer = 0
                else:
                    if gamepad_neutral:
                        gamepad_move = True
                        gamepad_neutral = False
                    else:
                        gamepad_pressed_timer += pygame.time.get_ticks() - gamepad_last_update
                if gamepad_pressed_timer > gamepad_repeat_delay:
                    gamepad_move = True
                    gamepad_pressed_timer -= gamepad_repeat_delay
                if gamepad_move:
                    if joystick_hat == (-1, 0):
                        self.move_update_circuit_grid_display(self.circuit_grid, MOVE_LEFT)
                    elif joystick_hat == (1, 0):
                        self.move_update_circuit_grid_display(self.circuit_grid, MOVE_RIGHT)
                    elif joystick_hat == (0, 1):
                        self.move_update_circuit_grid_display(self.circuit_grid, MOVE_UP)
                    elif joystick_hat == (0, -1):
                        self.move_update_circuit_grid_display(self.circuit_grid, MOVE_DOWN)
                gamepad_last_update = pygame.time.get_ticks()

                # Check left thumbstick position
                # left_thumb_x = joystick.get_axis(0)
                # left_thumb_y = joystick.get_axis(1)

            # Handle Input Events
            for event in pygame.event.get():
                pygame.event.pump()

                # if event.type != MOUSEMOTION:
                #     print("event: ", event)
                if event.type == QUIT:
                    going = False

                elif event.type == JOYBUTTONDOWN:
                    if event.button == BTN_A:
                        # Place X gate
                        self.circuit_grid.handle_input_x()
                        self.update_circ_viz()
                        pygame.display.flip()
                    elif event.button == BTN_X:
                        # Place Y gate
                        self.circuit_grid.handle_input_y()
                        self.update_circ_viz()
                        pygame.display.flip()
                    elif event.button == BTN_B:
                        # Place Z gate
                        self.circuit_grid.handle_input_z()
                        self.update_circ_viz()
                        pygame.display.flip()
                    elif event.button == BTN_Y:
                        # Place Hadamard gate
                        self.circuit_grid.handle_input_h()
                        self.update_circ_viz()
                        pygame.display.flip()
                    elif event.button == BTN_RIGHT_TRIGGER:
                        # Delete gate
                        self.circuit_grid.handle_input_delete()
                        self.update_circ_viz()
                        pygame.display.flip()
                    elif event.button == BTN_RIGHT_THUMB:
                        # Add or remove a control
                        self.circuit_grid.handle_input_ctrl()
                        self.update_circ_viz()
                        pygame.display.flip()

                elif event.type == JOYAXISMOTION:
                    # print("event: ", event)
                    if event.axis == AXIS_RIGHT_THUMB_X and joystick.get_axis(AXIS_RIGHT_THUMB_X) >= 0.95:
                        self.circuit_grid.handle_input_rotate(np.pi / 8)
                        self.update_circ_viz()
                        pygame.display.flip()
                    if event.axis == AXIS_RIGHT_THUMB_X and joystick.get_axis(AXIS_RIGHT_THUMB_X) <= -0.95:
                        self.circuit_grid.handle_input_rotate(-np.pi / 8)
                        self.update_circ_viz()
                        pygame.display.flip()
                    if event.axis == AXIS_RIGHT_THUMB_Y and joystick.get_axis(AXIS_RIGHT_THUMB_Y) <= -0.95:
                        self.circuit_grid.handle_input_move_ctrl(MOVE_UP)
                        self.update_circ_viz()
                        pygame.display.flip()
                    if event.axis == AXIS_RIGHT_THUMB_Y and joystick.get_axis(AXIS_RIGHT_THUMB_Y) >= 0.95:
                        self.circuit_grid.handle_input_move_ctrl(MOVE_DOWN)
                        self.update_circ_viz()
                        pygame.display.flip()

                elif event.type == KEYDOWN:
                    index_increment = 0
                    if event.key == K_ESCAPE:
                        going = False
                    elif event.key == K_a:
                        self.circuit_grid.move_to_adjacent_node(MOVE_LEFT)
                        self.circuit_grid.draw(screen)
                        pygame.display.flip()
                    elif event.key == K_d:
                        self.circuit_grid.move_to_adjacent_node(MOVE_RIGHT)
                        self.circuit_grid.draw(screen)
                        pygame.display.flip()
                    elif event.key == K_w:
                        self.circuit_grid.move_to_adjacent_node(MOVE_UP)
                        self.circuit_grid.draw(screen)
                        pygame.display.flip()
                    elif event.key == K_s:
                        self.circuit_grid.move_to_adjacent_node(MOVE_DOWN)
                        self.circuit_grid.draw(screen)
                        pygame.display.flip()
                    elif event.key == K_x:
                        self.circuit_grid.handle_input_x()
                        self.update_circ_viz()
                        pygame.display.flip()
                    elif event.key == K_y:
                        self.circuit_grid.handle_input_y()
                        self.update_circ_viz()
                        pygame.display.flip()
                    elif event.key == K_z:
                        self.circuit_grid.handle_input_z()
                        self.update_circ_viz()
                        pygame.display.flip()
                    elif event.key == K_h:
                        self.circuit_grid.handle_input_h()
                        self.update_circ_viz()
                        pygame.display.flip()
                    elif event.key == K_BACKSLASH:
                        self.circuit_grid.handle_input_delete()
                        self.update_circ_viz()
                        pygame.display.flip()
                    elif event.key == K_c:
                        # Add or remove a control
                        self.circuit_grid.handle_input_ctrl()
                        self.update_circ_viz()
                        pygame.display.flip()
                    elif event.key == K_UP:
                        # Move a control qubit up
                        self.circuit_grid.handle_input_move_ctrl(MOVE_UP)
                        self.update_circ_viz()
                        pygame.display.flip()
                    elif event.key == K_DOWN:
                        # Move a control qubit down
                        self.circuit_grid.handle_input_move_ctrl(MOVE_DOWN)
                        self.update_circ_viz()
                        pygame.display.flip()
                    elif event.key == K_LEFT:
                        # Rotate a gate
                        self.circuit_grid.handle_input_rotate(-np.pi/8)
                        self.update_circ_viz()
                        pygame.display.flip()
                    elif event.key == K_RIGHT:
                        # Rotate a gate
                        self.circuit_grid.handle_input_rotate(np.pi / 8)
                        self.update_circ_viz()
                        pygame.display.flip()

            if expectation_value_dirty:
                # expectation_grid.normalize_desired_unitary()
                self.expectation_grid.draw_expectation_grid()

                # TODO: Apply optimization
                rotation_gate_nodes = self.circuit_grid_model.get_rotation_gate_nodes()

                # initial_rotations = np.zeros(len(rotation_gate_nodes))
                initial_rotations = np.full(len(rotation_gate_nodes), np.pi)

                rotation_bounds = np.zeros((len(rotation_gate_nodes), 2))

                opt_rotations = self.optimize_rotations(self.expectation_value_objective_function,
                                                        initial_rotations, self.circuit_grid,
                                                        self.expectation_grid, rotation_gate_nodes)

                print('opt_rotations: ', opt_rotations)

                cost, basis_state_str = self.expectation_grid.calc_expectation_value()

                solution = np.zeros(NUM_STATE_DIMS)
                for idx, char in enumerate(basis_state_str):
                    solution[idx] = int(char)

                self.network_graph.set_solution(solution)

                self.update_circ_viz()

                # expectation_grid.zero_desired_unitary()
                expectation_value_dirty = False

        pygame.quit()

    def optimize_rotations(self, objective_function, x0, circuit_grid, expectation_grid, rotation_gate_nodes):

        # Tries to be plug-compatible with scipy.optimize.fmin_l_bfgs_b
        optimization_epochs = 1
        move_radians = np.pi / 8

        optimized_rotations = np.copy(x0)
        # min_distance = float("inf")

        # For each rotation this will be either 1 or -1, signifying direction of movement
        unit_direction_array = np.ones(len(optimized_rotations))

        min_distance = objective_function(optimized_rotations, circuit_grid, expectation_grid, rotation_gate_nodes)

        for epoch_idx in range(optimization_epochs):
            for rotations_idx in range(len(optimized_rotations)):
                cur_ang_rad = optimized_rotations[rotations_idx]
                proposed_cur_ang_rad = cur_ang_rad

                # Decide whether to increase or decrease angle
                unit_direction_array[rotations_idx] = 1
                if cur_ang_rad > np.pi:
                    unit_direction_array[rotations_idx] = -1
                proposed_cur_ang_rad += move_radians * unit_direction_array[rotations_idx]
                if 0.0 <= proposed_cur_ang_rad < np.pi * 2:
                    optimized_rotations[rotations_idx] = proposed_cur_ang_rad

                    temp_distance = objective_function(optimized_rotations, circuit_grid, expectation_grid, rotation_gate_nodes)
                    if temp_distance > min_distance:
                        # Moving in the wrong direction so restore the angle in the array and switch direction
                        optimized_rotations[rotations_idx] = cur_ang_rad
                        unit_direction_array[rotations_idx] *= -1
                    else:
                        # Moving in the right direction so use the proposed angle
                        cur_ang_rad = proposed_cur_ang_rad
                        min_distance = temp_distance

                    finished_with_while_loop = False
                    loop_iterations = 0
                    while not finished_with_while_loop:
                        loop_iterations += 1
                        proposed_cur_ang_rad += move_radians * unit_direction_array[rotations_idx]
                        if 0.0 <= proposed_cur_ang_rad < np.pi * 2:
                            optimized_rotations[rotations_idx] = proposed_cur_ang_rad
                            temp_distance = objective_function(optimized_rotations, circuit_grid, expectation_grid, rotation_gate_nodes)
                            if temp_distance > min_distance:
                                # Distance is increasing so restore the angle in the array and leave the loop
                                optimized_rotations[rotations_idx] = cur_ang_rad
                                finished_with_while_loop = True
                            elif loop_iterations > np.pi * 2 / move_radians:
                                print("Unexpected: Was in while loop over ",  loop_iterations, " iterations")
                                finished_with_while_loop = True
                            else:
                                # Distance is not increasing, so use the proposed angle
                                cur_ang_rad = proposed_cur_ang_rad
                                min_distance = temp_distance
                        else:
                            finished_with_while_loop = True
            print('min_distance: ', min_distance)

            objective_function(optimized_rotations, circuit_grid, expectation_grid, rotation_gate_nodes)
            print('exp_val: ', expectation_grid.calc_expectation_value())
        return optimized_rotations

    def expectation_value_objective_function(self, rotations_radians, circuit_grid,
                                             expectation_grid, rotation_gate_nodes):
        for idx in range(len(rotation_gate_nodes)):
            circuit_grid.rotate_gate_absolute(rotation_gate_nodes[idx], rotations_radians[idx])
            expectation_grid.set_circuit(circuit_grid.circuit_grid_model.compute_circuit())
            cost, basis_state = expectation_grid.calc_expectation_value()

            print("rotations_radians: ", rotations_radians, ", cost: ", cost, ", basis_state: ", basis_state)
        return cost


    # def update_circ_viz(circuit, circuit_grid_model, circuit_grid, top_sprites, right_sprites,
    #                     expectaton_grid):
    def update_circ_viz(self):
        self.screen.blit(self.background, (0, 0))
        circuit = self.circuit_grid_model.compute_circuit()
        self.expectation_grid.set_circuit(circuit)
        self.top_sprites.arrange()
        self.right_sprites.arrange()
        self.top_sprites.draw(self.screen)
        self.right_sprites.draw(self.screen)
        self.circuit_grid.draw(self.screen)
        pygame.display.flip()


    def move_update_circuit_grid_display(self, circuit_grid, direction):
        circuit_grid.move_to_adjacent_node(direction)
        circuit_grid.draw(screen)
        pygame.display.flip()


    def measure_circuit(self, circ, initial_bit_str, unitary_grid):
        # Use the BasicAer qasm_simulator backend
        from qiskit import BasicAer
        backend_sim = BasicAer.get_backend('qasm_simulator')

        # Initialize each wire
        init_qr = QuantumRegister(NUM_QUBITS, 'q')

        init_circ = QuantumCircuit(init_qr)

        for bit_idx in range(0, NUM_QUBITS):
            if int(initial_bit_str[bit_idx]) == 1:
                init_circ.x(init_qr[NUM_QUBITS - bit_idx - 1])
            else:
                init_circ.iden(init_qr[NUM_QUBITS - bit_idx - 1])

        init_circ.barrier(init_qr)

        # Create a Quantum Register with 4 qubits
        qr = QuantumRegister(NUM_QUBITS, 'q')

        # Create a Classical Register with 4 bits
        cr = ClassicalRegister(NUM_QUBITS, 'c')

        # Create the measurement portion of a quantum circuit
        meas_circ = QuantumCircuit(qr, cr)

        # Create a barrier that separates the gates from the measurements
        meas_circ.barrier(qr)

        # Measure the qubits into the classical registers
        meas_circ.measure(qr, cr)

        # Add the measurement circuit to the original circuit
        complete_circuit = init_circ + circ + meas_circ

        # Execute the circuit on the qasm simulator, running it 1000 times.
        job_sim = execute(complete_circuit, backend_sim, shots=1)

        # Grab the results from the job.
        result_sim = job_sim.result()

        # Print the counts, which are contained in a Python dictionary
        counts = result_sim.get_counts(complete_circuit)
        # print(counts)
        basis_state_str = list(counts.keys())[0]
        # print ("basis_state_str: ", basis_state_str)

        return basis_state_str



if __name__ == "__main__":
    VQEPlayground().main()