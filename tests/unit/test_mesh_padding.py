"""Verify mesh_padding fix: padding EXPANDS the extent correctly."""

import cartopy.crs as ccrs
import matplotlib
import pytest


matplotlib.use("Agg")

from rendering.layers.base_map import calc_extent, draw_mesh_lines, get_map_extent


# bounds from shape_service: [min_lon, min_lat, max_lon, max_lat]
BOUNDS = [119.0, 29.0, 122.0, 31.0]

# calc_extent returns: [min_lon, max_lon, min_lat, max_lat]
RAW_EXTENT = [119.0, 122.0, 29.0, 31.0]


def _make_config(**overrides):
    c = {
        "width": 700,
        "height": 700,
        "show_border": False,
        "show_mesh": False,
        "mesh_padding": "0.0, 0.0, 0.0, 0.0",
    }
    c.update(overrides)
    return c


class TestCalcExtent:
    def test_no_padding_returns_raw_extent(self):
        extent = calc_extent(BOUNDS, _make_config())
        assert extent == RAW_EXTENT

    def test_uniform_padding_expands_all_directions(self):
        extent = calc_extent(BOUNDS, _make_config(mesh_padding="0.5, 0.5, 0.5, 0.5"))
        assert extent == [118.5, 122.5, 28.5, 31.5]

    def test_all_zero_no_effect(self):
        extent = calc_extent(BOUNDS, _make_config(mesh_padding="0.0, 0.0, 0.0, 0.0"))
        assert extent == RAW_EXTENT

    def test_padding_order_top_right_bottom_left(self):
        """pad format: [top, right, bottom, left] → EXPAND in each direction."""
        extent = calc_extent(BOUNDS, _make_config(mesh_padding="1.0, 2.0, 3.0, 4.0"))
        assert extent[0] == pytest.approx(119.0 - 4.0)  # left: min_lon -= 4
        assert extent[1] == pytest.approx(122.0 + 2.0)  # right: max_lon += 2
        assert extent[2] == pytest.approx(29.0 - 3.0)  # bottom: min_lat -= 3
        assert extent[3] == pytest.approx(31.0 + 1.0)  # top: max_lat += 1

    def test_mesh_padding_independent_of_show_mesh(self):
        extent_no_mesh = calc_extent(BOUNDS, _make_config(show_mesh=False, mesh_padding="0.3, 0.3, 0.3, 0.3"))
        extent_with_mesh = calc_extent(BOUNDS, _make_config(show_mesh=True, mesh_padding="0.3, 0.3, 0.3, 0.3"))
        assert extent_no_mesh == extent_with_mesh

    def test_padding_expands_extent_size(self):
        raw = calc_extent(BOUNDS, _make_config())
        padded = calc_extent(BOUNDS, _make_config(mesh_padding="1.0, 1.0, 1.0, 1.0"))
        assert (padded[1] - padded[0]) > (raw[1] - raw[0])  # lon range larger
        assert (padded[3] - padded[2]) > (raw[3] - raw[2])  # lat range larger


class TestDrawMeshLines:
    def test_show_false_just_turns_off_axis(self):
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(subplot_kw={"projection": ccrs.PlateCarree()})
        result = draw_mesh_lines(ax, _make_config())
        assert result is None
        plt.close(fig)

    def test_show_true_draws_gridlines(self):
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(subplot_kw={"projection": ccrs.PlateCarree()})
        result = draw_mesh_lines(ax, _make_config(show_border=True, show_mesh=True))
        assert result is None
        plt.close(fig)


class TestGetMapExtent:
    def test_padding_makes_extent_larger(self):
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(subplot_kw={"projection": ccrs.PlateCarree()})
        raw = get_map_extent(ax, BOUNDS, _make_config())
        padded = get_map_extent(ax, BOUNDS, _make_config(mesh_padding="0.5, 0.5, 0.5, 0.5"))
        assert (padded[1] - padded[0]) > (raw[1] - raw[0])
        assert (padded[3] - padded[2]) > (raw[3] - raw[2])
        plt.close(fig)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
