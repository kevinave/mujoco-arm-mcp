"""arm_common.fk() claims to agree with MuJoCo's own numbers — hold it to that.

The analytic solution and MuJoCo derive the tip position from the same two hinge
angles, so comparing them across a grid of poses checks the link lengths, the
base offset and the sign conventions all at once. mj_forward needs no GUI, so
this runs headless.
"""
import itertools
import math

import mujoco
import pytest

import arm_common

GRID = [-90, -45, 0, 45, 90]


@pytest.fixture(scope="module")
def sim():
    model = mujoco.MjModel.from_xml_string(arm_common.XML)
    return model, mujoco.MjData(model)


@pytest.mark.parametrize("j1_deg,j2_deg", list(itertools.product(GRID, GRID)))
def test_fk_agrees_with_mujoco(sim, j1_deg, j2_deg):
    model, data = sim
    data.qpos[0] = math.radians(j1_deg)
    data.qpos[1] = math.radians(j2_deg)
    mujoco.mj_forward(model, data)
    tip = data.site("tip").xpos

    x, z = arm_common.fk(j1_deg, j2_deg)

    # fk() rounds to 3 decimals, so 1e-3 is the tightest honest tolerance.
    assert x == pytest.approx(float(tip[0]), abs=1e-3)
    assert z == pytest.approx(float(tip[2]), abs=1e-3)
