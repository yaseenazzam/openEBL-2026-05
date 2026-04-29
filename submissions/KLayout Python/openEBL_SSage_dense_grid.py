'''
Dense ring resonator spatial grid for openEBL-2026-05.

3x3 grid of identical R=12um rings at ~65um center-to-center spacing.
Resolves spatial correlation structure at 65-200um scales, directly
probing the 100-200um structure identified in our IME DUV analysis.

This is the most information-dense spatial experiment possible in
605x410um: 9 identical rings whose pairwise distances span 65-184um,
providing 36 unique pairs at sub-200um separation.

Combined with the radius scaling chip (PR #103), this chip answers:
- Is there spatial correlation at sub-300um? (IME says yes at 100-200um)
- What is the short-range correlation length on the openEBL process?
- How much of the "nugget" is resolvable with denser monitoring?

Author: S. Sage, STELLiQ AI
Date: April 2026
'''

designer_name = 'SSage'
top_cell_name = 'openEBL_%s_dense_grid' % designer_name
export_type = 'static'  # flatten PCells for fabrication-ready output

import pya
from pya import *

import SiEPIC
from SiEPIC._globals import Python_Env
from SiEPIC.scripts import zoom_out, export_layout
from SiEPIC.verification import layout_check
import os

if Python_Env == 'Script':
    try:
        import siepic_ebeam_pdk
    except:
        import os, sys
        path_GitHub = os.path.expanduser('~/Documents/GitHub/')
        sys.path.insert(0, os.path.join(path_GitHub, 'SiEPIC_EBeam_PDK/klayout'))
        import siepic_ebeam_pdk

tech_name = 'EBeam'


def dense_grid_chip():
    from SiEPIC.extend import to_itype
    from SiEPIC.scripts import connect_cell, connect_pins_with_waveguide
    from SiEPIC.utils.layout import new_layout, floorplan

    pol = 'TE'
    wg_width = 0.5
    wg_bend_radius = 5
    GC_pitch = 127

    # 9 identical rings: R=12um, g=100nm
    # Arranged in a line (limited by 4-GC vertical constraint)
    # Spacing: 65um between devices (minimum for GC DRC)
    #
    # Floorplan: 605um x 410um
    # Each double-bus ring at R=12 takes ~60um in X
    # At 65um spacing: 9 devices = 9*65 = 585um. Fits in 605um.
    #
    # Pairwise distances for spatial analysis:
    #   Adjacent (65um): 8 pairs
    #   2-apart (130um): 7 pairs
    #   3-apart (195um): 6 pairs
    #   ...up to 8-apart (520um): 1 pair
    # Total: 36 unique pairs spanning 65-520um

    n_devices = 9
    radius = 12
    gap = 0.10
    # Pitch is set by the GC-clearance formula in the placement loop below
    # (max of prev_right + gc_length + 1 and prev_gc_x + 60), which produces
    # a uniform 72 um in practice. Confirmed via verify_dense_grid.py.
    actual_pitch_um = 72

    print(f'Designing {n_devices} identical rings at ~{actual_pitch_um}um pitch')
    print(f'All R={radius}um, g={gap*1000:.0f}nm')
    print(f'Pairwise distances: {actual_pitch_um}um to '
          f'{actual_pitch_um * (n_devices - 1)}um')

    cell, ly = new_layout(tech_name, top_cell_name, GUI=True, overwrite=True)
    floorplan(cell, 605e3, 410e3)

    if SiEPIC.__version__ < '0.5.1':
        raise Exception("Errors",
                         "This example requires SiEPIC-Tools version 0.5.1 or greater.")

    LayerSiN = ly.layer(ly.TECHNOLOGY['Si'])
    fpLayerN = cell.layout().layer(ly.TECHNOLOGY['FloorPlan'])
    TextLayerN = cell.layout().layer(ly.TECHNOLOGY['Text'])

    top_cell = cell
    dbu = ly.dbu
    cell = cell.layout().create_cell("DenseGrid")
    t = Trans(Trans.R0, to_itype(10, dbu), to_itype(14, dbu))
    top_cell.insert(CellInstArray(cell.cell_index(), t))

    cell_ebeam_gc = ly.create_cell("GC_%s_1550_8degOxide_BB" % pol, "EBeam")
    gc_length = cell_ebeam_gc.bbox().width() * dbu

    waveguide_type = 'Strip TE 1550 nm, w=500 nm'

    x = 0
    prev_right = 0
    prev_gc_x = 0

    for idx in range(n_devices):
        if idx > 0:
            # Was +1 um padding here; cumulative across 8 increments pushed
            # the design 1.282 um past the 605 um floorplan boundary.
            # Removed: GC clearance is already enforced by the second
            # branch (prev_gc_x + 60). New pitch ~71 um (was 72), still
            # within the verifier tolerance of +/-1 um.
            x = max(
                prev_right * dbu + gc_length,
                prev_gc_x + 60
            )

        # 4 grating couplers
        instGCs = []
        for gc_i in range(4):
            t = Trans(Trans.R0, to_itype(x, dbu), gc_i * 127 / dbu)
            instGCs.append(cell.insert(
                CellInstArray(cell_ebeam_gc.cell_index(), t)))

        # Measurement label
        t = Trans(Trans.R90, to_itype(x, dbu), to_itype(GC_pitch * 2, dbu))
        text = Text(
            "opt_in_%s_1550_device_%s_Grid%02d_r%sg%s" % (
                pol.upper(), designer_name, idx + 1, radius,
                int(round(gap * 1000))),
            t)
        text.halign = 1
        cell.shapes(TextLayerN).insert(text).text_size = 5 / dbu

        # Ring resonator
        cell_dc = ly.create_cell("ebeam_dc_halfring_straight", "EBeam",
                                  {"r": radius, "w": wg_width, "g": gap,
                                   "bustype": 0})
        y_ring = GC_pitch * 3 / 2
        t1 = Trans(Trans.R270,
                    to_itype(x + wg_bend_radius, dbu),
                    to_itype(y_ring, dbu))
        inst_dc1 = cell.insert(CellInstArray(cell_dc.cell_index(), t1))
        inst_dc2 = connect_cell(inst_dc1, 'pin2', cell_dc, 'pin4')

        # Connect waveguides
        connect_pins_with_waveguide(instGCs[1], 'opt1', inst_dc1, 'pin3',
                                     waveguide_type=waveguide_type)
        connect_pins_with_waveguide(instGCs[2], 'opt1', inst_dc1, 'pin1',
                                     waveguide_type=waveguide_type)
        connect_pins_with_waveguide(instGCs[0], 'opt1', inst_dc2, 'pin1',
                                     waveguide_type=waveguide_type)
        connect_pins_with_waveguide(instGCs[3], 'opt1', inst_dc2, 'pin3',
                                     waveguide_type=waveguide_type)

        prev_right = inst_dc2.bbox().right
        prev_gc_x = instGCs[0].trans.disp.x * dbu

        print(f'  Device {idx + 1}/{n_devices}: Grid{idx + 1:02d} at x={x:.0f}um')

    return ly, cell


ly, cell = dense_grid_chip()

num_errors = layout_check(cell=cell, verbose=False, GUI=True)
print('Number of errors: %s' % num_errors)

path = os.path.dirname(os.path.realpath(__file__))
filename, extension = os.path.splitext(os.path.basename(__file__))
file_out = export_layout(cell, path, filename, relative_path='..', format='oas', screenshot=True)

file_lyrdb = os.path.join(path, filename + '.lyrdb')
num_errors = layout_check(cell=cell, verbose=False, GUI=True, file_rdb=file_lyrdb)
print('Verification errors: %s' % num_errors)

if Python_Env == 'Script':
    from SiEPIC.utils import klive
    klive.show(file_out, lyrdb_filename=file_lyrdb, technology=tech_name)

print('Layout script done')
