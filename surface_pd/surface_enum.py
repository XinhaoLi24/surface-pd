"""
TODO: Insert module description here.

"""

import copy
import numpy as np

from pymatgen.core import Structure
from pymatgen.core.surface import get_slab_regions
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

__author__ = "Xinhao Li"
__email__ = "xl2778@columbia.edu"
__date__ = "2021-01-05"

# %% Wrap back and equal lattices check
EPS = np.finfo(np.double).eps



class IncompatibleLatticeError(Exception):
    pass


class NoInversionSymmetryError(Exception):
    pass


def wrap_pbc(coo, slab_direction=2, tolerance=0.1):
    """
    Wrap fractional coordinates back into the unit cell.

    Arguments:
      coo (ndarray): 3-vector of fractional coordinates
      tolerance (float): tolerance in multiples of the lattice vector applied
        when wrapping in direction of the slab, so that atoms at the bottom
        of the slab are not wrapped to the top of the unit cell
      ToDo: tolerance could be determined automatically based on the center
            of the vacuum region
    Returns:
      0.0 <= coo[i] < 1.0  for the directions within the slab planes and
      -tolerance <= coo[i] < (1.0 - tolerance)  for the slab direction

    """
    bounds = np.array([0.0, 0.0, 0.0])
    bounds[slab_direction] = tolerance
    for i in range(3):
        while (coo[i] < -bounds[i]):
            coo[i] += 1.0
        while (coo[i] >= (1.0 - bounds[i] - EPS)):
            coo[i] -= 1.0
    return coo


def equal_lattices(lat1, lat2, dtol=0.001, atol=0.01):
    lencheck = not np.any(
        np.abs(np.array(lat1.lengths) - np.array(lat2.lengths)) > dtol)
    angcheck = not np.any(
        np.abs(np.array(lat1.angles) - np.array(lat2.angles)) > atol)
    return lencheck and angcheck


def group_atoms_by_layer(o_layer, diff=0.01, max_diff=0.03):
    """
    This function is used to group misclassified atoms into the right
    layers. For example, c_atom1 = 0.01, c_atoms2 = 0.02, they should be
    classified in one layer. But actually they are not. So this function
    here will search the difference between two closest atoms, if the
    difference is smaller than diff, they will be regrouped in the same
    layer.

    Args:
        o_layer: dictionary which contains different c fractional
          coordinates as keys and number of atoms as values.
        diff: Accepted c fractional coordinates difference between two
          atoms.
        max_diff: Maximum accepted c fractional coordinates difference
          between two atoms.

    Returns: dictionary which contains different c fractional
      coordinates as keys and number of atoms as values.

    """
    height_sorted = sorted(o_layer.keys(), reverse=True)
    res = dict()
    excluded_heights = set()
    for height in height_sorted:
        if height in excluded_heights:
            continue
        res[height] = o_layer[height]
        for i in range(1, int(max_diff / diff) + 1):
            curr_height = height - i * diff
            if curr_height not in o_layer:
                break
            res[height] += o_layer[curr_height]
            excluded_heights.add(curr_height)
    return res


def layer_classification(input_structure):
    """
    This function is used to determine the c fractional coordinates of
    central region of the slab models as well as the surface metal and O
    atoms.

    Args:
        input_structure: any slab models

    Returns: upper limit and lower limit of the central region of the
      slab, surface metal and O c fractional coordinates

    """
    structure = input_structure
    Li_layers = {}
    TM_layers = {}
    O_layers = {}
    for s in structure:
        if 'Li' in s:
            # Since the c fractional coordinates of atoms even in the
            # exactly same layers are not identical, therefore, all c
            # fractional coordinates will be rounded to 2 decimal. Any
            # misclassified atoms will be regouped by
            # "group_atoms_by_layer" function.
            if round(s.frac_coords[2], 2) not in Li_layers:
                Li_layers[round(s.frac_coords[2], 2)] = 1
            else:
                Li_layers[round(s.frac_coords[2], 2)] += 1
        elif 'Ni' in s:
            if round(s.frac_coords[2], 2) not in TM_layers:
                TM_layers[round(s.frac_coords[2], 2)] = 1
            else:
                TM_layers[round(s.frac_coords[2], 2)] += 1
        else:
            if round(s.frac_coords[2], 2) not in O_layers:
                O_layers[round(s.frac_coords[2], 2)] = 1
            else:
                O_layers[round(s.frac_coords[2], 2)] += 1
    Li_layers = group_atoms_by_layer(Li_layers)
    TM_layers = group_atoms_by_layer(TM_layers)
    O_layers = group_atoms_by_layer(O_layers)

    center_sites = []
    for s in structure:
        if ('selective_dynamics' in s.properties
                and not any(s.properties['selective_dynamics'])):
            center_sites.append(copy.deepcopy(s))
    center = Structure.from_sites(center_sites)
    # center.to(fmt='poscar', filename='center.vasp') ## Save center structure
    center_region = get_slab_regions(center)
    # print(center_region[0][0])
    lower_limit = center_region[0][0]
    upper_limit = center_region[0][1]
    if len(Li_layers) > len(TM_layers):
        surface_Li = sorted(Li_layers.items())[-1][0]
        surface_O = sorted(O_layers.items())[-1][0]
        # print ('The structure is terminated with Li layers')
        # print ('Ni layer is the central layer.')
        return lower_limit, upper_limit, surface_Li, surface_O
    elif len(Li_layers) < len(TM_layers):
        surface_TM = sorted(TM_layers.items())[-1][0]
        surface_O = sorted(O_layers.items())[-1][0]
        # print ('The structure is terminated with Ni layers')
        # print('Li layer is the central layer.')
        return lower_limit, upper_limit, surface_TM, surface_O
    else:
        surface_TM_Li = sorted(TM_layers.items())[-1][0]
        surface_O = sorted(O_layers.items())[-1][0]
        # print('The structure has polar surfaces.')
        return lower_limit, upper_limit, surface_TM_Li, surface_O


def symmetrize_top_base(target_slab, symprec=0.03, direction=2):
    """
    This function is used to symmetrize the enumerated slab models using
    top surface as base. The general idea is exactly the same as
    Prof. Urban's version. But the main difference is that here, the
    inversion symmetry center is determined based on the central region
    only. This is because the input structure of this function is not
    symmetry at all because the top surface of slab is substituted with
    other elements and also it is enumerated based on provided
    compositions. Therefore using the whole slab to detect the inversion
    symmetry does not work.  Here, we used the returned parameters from
    "layer_classification" function to determine the c fractional
    coordinates of the central region. And then just use the central
    region to obtain the inversion symmetry center.

    Args:
        target_slab: input structure which contains vacancies and
          substituted atoms on the surface
        symprec: tolerance for symmetry detection
        direction: lattice direction perpendicular to the surface

    Returns: symmetrized slab models

    """
    # Load structure which is going to symmetrize
    slab_tgt = target_slab  # Used in completed code

    # Use center region to get the inversion symmetry center nad
    # rotation matrix
    """
    Upper limit and lower limit of the target slab have been determined by
    the layer_classification function above.
    """
    lower_limit = layer_classification(slab_tgt)[0]
    upper_limit = layer_classification(slab_tgt)[1]
    slab_ref_site = []
    for s in slab_tgt:
        if lower_limit - 0.01 < s.frac_coords[2] < upper_limit + 0.01:
            slab_ref_site.append(copy.deepcopy(s))
    slab_ref = Structure.from_sites(slab_ref_site)

    # Determine symmetry operations of the center reference slab and make sure
    # the reference slab has an inversion center
    sga = SpacegroupAnalyzer(slab_ref, symprec=symprec)
    if not sga.is_laue():  # has Laue symmetry (centro-symmetry)
        raise NoInversionSymmetryError(
            "The target slab does not have inversion symmetry.  Try "
            "increasing the tolerance for symmetry detection with the "
            "'--symprec' flag.")

    # get the inversion operation and the inversion center (origin)
    ops = sga.get_symmetry_operations()
    # This will return lots of symmetry operations, one of them is
    # inversion symmetry.
    inversion = ops[1]
    assert (np.all(inversion.rotation_matrix == -np.identity(3)))
    origin = inversion.translation_vector / 2

    # wrap target slab structure to unit cell
    for s in slab_tgt:
        s.frac_coords = wrap_pbc(s.frac_coords, slab_direction=direction)

    # Symmetrized structure models based on top only
    top_sites = []
    bottom_sites = []
    center_sites = []
    for s in [s for s in slab_tgt
              if s.frac_coords[direction] > origin[direction]]:
        if ('selective_dynamics' in s.properties
                and not any(s.properties['selective_dynamics'])):
            center_sites.append(copy.deepcopy(s))
        else:
            top_sites.append(copy.deepcopy(s))
    for s in [s for s in slab_tgt
              if s.frac_coords[direction] < origin[direction]]:
        if ('selective_dynamics' in s.properties
                and not any(s.properties['selective_dynamics'])):
            center_sites.append(copy.deepcopy(s))
        else:
            bottom_sites.append(copy.deepcopy(s))
    center_sites.extend([copy.deepcopy(s) for s in slab_tgt
                         if s.frac_coords[direction] == origin[direction]])

    sites = center_sites[:] + top_sites[:]
    for s in top_sites:
        s2 = copy.deepcopy(s)
        s2.frac_coords = inversion.operate(s.frac_coords)
        sites.append(s2)
    symmetrized_slab_top = Structure.from_sites(sites)
    for s in symmetrized_slab_top:
        s.frac_coords = wrap_pbc(s.frac_coords, slab_direction=direction)
    symmetrized_slab_top = symmetrized_slab_top.get_sorted_structure()
    return symmetrized_slab_top


def surface_substitute(target_slab, subs1, subs2, direction=2):
    """
    This function is used to substitute surface atoms with desired atoms
    in order to use enumerate tool easier.

    :param target_slab: Beginning structure model used
    :param subs1: Substitution atom for O atom
    :param subs2: Substitution atom for Li atom
    :param direction: Define which fractional coordinate is used.
    :return: Substituted structure model

    """
    # Load structure
    slab_tgt = Structure.from_file(target_slab)

    # New way
    max_frac_O = layer_classification(slab_tgt)[-1]
    max_frac_Li = layer_classification(slab_tgt)[-2]
    # Surface (outermost) TM/Li
    distance = (layer_classification(slab_tgt)[2]
                - layer_classification(slab_tgt)[1])
    # c fraction coords - uppper limit of center fixed region

    # Define criteria to determine surface O and Li atoms
    surface_O = []
    surface_Li = []
    for s in slab_tgt:
        if (max_frac_O - s.frac_coords[direction] < 0.02) and ('O' in s):
            surface_O.append(copy.deepcopy(s))
        if ((max_frac_Li - s.frac_coords[direction] < distance - 0.02)
            and ('Li' in s)):
            surface_Li.append(copy.deepcopy(s))

    # Extract indices for surface O and Li atoms in target slab model
    def indices(tgt_idx, ref_idx):
        idx = []
        for i, s in enumerate(tgt_idx):
            for j, t in enumerate(ref_idx):
                if t == s:
                    idx.append(i)
        return idx

    idx_surface_O = indices(slab_tgt, surface_O)
    idx_surface_Li = indices(slab_tgt, surface_Li)

    # Substitute surface O and Li atoms with F (fluorine) and Na (sodium)
    slab_surface_substitute = slab_tgt.copy()
    for i in range(len(slab_surface_substitute)):
        if i in idx_surface_O:
            slab_surface_substitute.replace(
                i, subs1,
                properties={'selective_dynamics': [True, True, True]})
        if i in idx_surface_Li:
            slab_surface_substitute.replace(
                i, subs2,
                properties={'selective_dynamics': [True, True, True]})
    # slab_surface_substitute.to(fmt='poscar', filename='104-subs.vasp')
    return slab_surface_substitute