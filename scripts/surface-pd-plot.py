#!/usr/bin/env python

"""
This code will be used to construct the surface phase diagram.
"""

__author__ = "Xinhao Li"
__email__ = "xl2778@columbia.edu"
__date__ = "2022-08-05"

import argparse

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

# from surface_pd.surface_plot import (convert_numbers, get_ticks_and_levels,
#                                      get_surface_energy, find_stable_phases,
#                                      get_labels, get_check_phases,
#                                      get_the_shift_energy,
#                                      standardize_pd_data,
#                                      get_TM_species)
from surface_pd.plot.plot import Plot

rcparams = {"font.size": 20,
            "legend.frameon": False,
            "xtick.top": True,
            "xtick.direction": "in",
            "xtick.minor.visible": True,
            "xtick.major.size": 16,
            "xtick.minor.size": 8,
            "ytick.right": True,
            "ytick.direction": "in",
            "ytick.minor.visible": True,
            "ytick.major.size": 16,
            "ytick.minor.size": 8}


def surface_pd_plot(data_files,
                    low_T, high_T,
                    color_Li=False,
                    color_O=False,
                    functional="PBE+U",
                    discharge=False,
                    save=False):
    # Create x and y axes
    V = np.linspace(0.0, 5.0, 500)
    T = np.linspace(low_T, high_T, 500)
    V_mesh, T_mesh = np.meshgrid(V, T)

    # Get the number of files
    num_files = len(data_files)

    # # Get the symbol of TM species
    # TM_species = get_TM_species(data_files[0])

    if num_files != 1:
        checked_phases = []
        df = []
        for data in data_files:
            temp_df = pd.read_table(data, sep="\s+", index_col=0)

            # Initialize the Plot class
            temp_plot = Plot(dataframe=temp_df,
                             lithium_like_species='Li',
                             oxygen_like_species='O',
                             V=V_mesh,
                             T=T_mesh,
                             functional=functional)
            # Standardize the surface pd data (with the same number of TM
            # species)
            temp_df = temp_plot.standardize_pd_data().dataframe
            # temp_df = standardize_pd_data(temp_df, TM_species=TM_species)
            # Get the phases that will be used to calcualte the shift energy
            checked_phases.append(temp_plot.get_check_phases())
            # checked_phases.append(get_check_phases(temp_df))
            df.append(temp_df)

        # Combine all dataframes
        df = pd.concat(df)

        # Calculate the shift energy for the polar surface only
        shift_energy = temp_plot.get_the_shift_energy(
            checked_phases=checked_phases)
        # shift_energy = get_the_shift_energy(checked_phases,
        #                                     TM_species,
        #                                     functional)
        # print(shift_energy)
        # Get surface energy
        plot = Plot(dataframe=df,
                    lithium_like_species='Li',
                    oxygen_like_species='O',
                    V=V_mesh,
                    T=T_mesh,
                    functional=functional)

        temp_G = plot.get_surface_energy()
        # temp_G = get_surface_energy(df, TM_species,
        #                             V_mesh, T_mesh,
        #                             functional=functional)
        shifted_G = temp_G[int(len(temp_G) / num_files):] + shift_energy
        # shifted_G = temp_G[int(len(temp_G) / len(data_files)):] + shift_energy
        G = np.append(temp_G[0:int(len(temp_G) / num_files)], shifted_G)
        # G = np.append(temp_G[0:int(len(temp_G) / len(data_files))], shifted_G)
    else:
        # Read data file
        df = pd.read_table(data_files[0], sep="\s+", index_col=0)
        plot = Plot(dataframe=df,
                    lithium_like_species='Li',
                    oxygen_like_species='O',
                    V=V_mesh,
                    T=T_mesh,
                    functional=functional)
        plot.standardize_pd_data()
        # df = standardize_pd_data(df, TM_species=TM_species)

        # Get surface energy
        G = plot.get_surface_energy()
        # G = get_surface_energy(df, TM_species,
        #                        V_mesh, T_mesh,
        #                        functional=functional)

    # Split an array into multiple sub-arrays
    stable_phases_index, ticks = plot.find_stable_phases()
    # stable_phases_index = find_stable_phases(G, df)

    # Get unique tick labels
    # ticks = np.unique([stable_phases_index])

    # Convert unique phases into a continuous phase number
    converted_stable_phases_index = plot.convert_numbers()
    # converted_stable_phases_index = convert_numbers(stable_phases_index, ticks)

    # Colorbar related parameters
    ticky, global_levels = plot.get_ticks_and_levels()
    # ticky, global_levels = get_ticks_and_levels(converted_stable_phases_index)

    # Reshape the array
    stable_phases_reshaped_global = np.reshape(converted_stable_phases_index,
                                               (T.size, V.size))

    if color_Li:
        if len(data_files) != 1:
            boundary = int(len(df) / len(data_files))
            for i in range(len(stable_phases_index)):
                if stable_phases_index[i] < boundary:
                    stable_phases_index[i] %= 5
                else:
                    stable_phases_index[i] = stable_phases_index[i] % 5 + 25
        else:
            stable_phases_index = stable_phases_index % 5

        ticks = np.unique([stable_phases_index])

        converted_stable_phases_index = convert_numbers(stable_phases_index,
                                                        ticks)
        stable_phases_reshaped = np.reshape(converted_stable_phases_index,
                                            (T.size, V.size))

        # temp_plot used
        ticky, levels = get_ticks_and_levels(converted_stable_phases_index)
        labels = get_labels(data_files, df, species=["Li"], ticks=ticks)
        cmap = "Greens_r"
        fig = plt.figure(figsize=(9.5, 6))

    elif color_O:
        # if len(data_files) != 1:
        #     boundary = int(len(df) / len(data_files))
        #     for i in range(len(stable_phases_index)):
        #         if stable_phases_index[i] < boundary:
        #             stable_phases_index[i] = stable_phases_index[i] // 5 * 5
        #         else:
        #             stable_phases_index[i] = (stable_phases_index[i] // 5 *
        #                                       5 + 25)
        # else:
        #     stable_phases_index = stable_phases_index % 5

        stable_phases_index = stable_phases_index // 5 * 5
        # print(np.unique(stable_phases_index))
        stable_phases_index = [x - 5 if x == 25 else x for x in
                               stable_phases_index]

        ticks = np.unique([stable_phases_index])
        # print(ticks)
        converted_stable_phases_index = convert_numbers(stable_phases_index,
                                                        ticks)

        stable_phases_reshaped = np.reshape(converted_stable_phases_index,
                                            (T.size, V.size))

        # temp_plot used
        ticky, levels = get_ticks_and_levels(converted_stable_phases_index)
        labels = get_labels(data_files, df, species=["O"], ticks=ticks)
        cmap = "Reds_r"
        fig = plt.figure(figsize=(9.5, 6))
    else:
        stable_phases_reshaped = stable_phases_reshaped_global
        # temp_plot used
        ticky, levels = get_ticks_and_levels(converted_stable_phases_index)
        labels = get_labels(data_files, df,
                            species=["Li", "O"], ticks=ticks)
        cmap = 'tab20c'
        fig = plt.figure(figsize=(10.5, 6))

    plt.rcParams.update(rcparams)
    ax = fig.add_subplot(111)
    # ax = plt.axes(projection='3d')
    ax.contour(V, T, stable_phases_reshaped_global, levels=global_levels,
               colors="black", linewidths=2)
    PD = ax.contourf(V, T, stable_phases_reshaped,
                     levels=levels, cmap=cmap)
    ax.set_xlabel('Potential vs. Li/Li$^+$ (V)', fontsize=20)
    ax.set_ylabel('Temperature (K)', fontsize=20)
    if discharge:
        ax.invert_xaxis()
    else:
        pass
    colorbar = fig.colorbar(PD, ticks=ticky, pad=0.05)
    colorbar.ax.set_yticklabels(labels)
    colorbar.ax.tick_params(size=0)
    colorbar.ax.minorticks_off()
    plt.tight_layout()
    if save:
        if discharge:
            plt.savefig('discharge-surface-pd.pdf', dpi=500)
        else:
            plt.savefig('charge-surface-pd.pdf', dpi=500)
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__ + "\n{} {}".format(__date__, __author__),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "surface_pd_data",
        help="Path to the surface pd data.",
        nargs="+",
        type=str
    )

    parser.add_argument(
        "--low-T", "-lt",
        help="Low temperature boundary",
        type=float,
        default=1
    )

    parser.add_argument(
        "--high-T", "-ht",
        help="High temperature boundary",
        type=float,
        default=1500
    )

    parser.add_argument(
        "--color-by-Li-content", "-cl",
        help="Whether color the surface pd by the Li content.",
        action="store_true"
    )

    parser.add_argument(
        "--color-by-O-content", "-co",
        help="Whether color the surface pd by the O content.",
        action="store_true"
    )

    parser.add_argument(
        "--functional", "-f",
        help="Functional used to perform the calculations.",
        type=str,
        default="PBE+U"
    )

    parser.add_argument(
        '--discharge', '-d',
        help='If the surface pd represents charge or discharge',
        action='store_true'
    )

    parser.add_argument(
        '--save', '-s',
        help='Whether to save the charge/discharge surface pd.',
        action='store_true'
    )

    args = parser.parse_args()

    surface_pd_plot(args.surface_pd_data,
                    args.low_T,
                    args.high_T,
                    args.color_by_Li_content,
                    args.color_by_O_content,
                    args.functional,
                    args.discharge,
                    args.save
                    )
