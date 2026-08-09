import numpy as np
import pytest

from transientwave.circuit_architecture import (
    TW1ACircuitProfile,
    bits_for_absolute_lsb,
    decompose_local_symmetric_q,
    gradient_hold_seconds,
    gradient_traversal_ticks,
    grid_edges,
    max_grid_degree,
    recompose_local_symmetric_q,
    required_self_path_full_scale,
    retention_time_constant_seconds,
    self_bits_matching_edge_lsb,
    signed_midtread_positive_codes,
)


def test_grid_has_64_nodes_and_112_edges():
    p = TW1ACircuitProfile()
    assert p.nodes == 64
    assert p.edges == 112
    assert len(grid_edges()) == 112
    assert max_grid_degree() == 4


def test_rank_one_edge_plus_self_decomposition_is_exact():
    rng = np.random.default_rng(23)
    n = 16
    edges = grid_edges(4, 4)
    Q = np.diag(rng.uniform(-1.2, 1.2, size=n))
    for i, j in edges:
        q = rng.uniform(-0.2, 0.2)
        Q[i, j] = q
        Q[j, i] = q
    d, a = decompose_local_symmetric_q(Q, edges=edges)
    recovered = recompose_local_symmetric_q(d, a)
    assert np.allclose(recovered, Q, atol=1e-12, rtol=0.0)


def test_nonlocal_q_is_rejected():
    Q = np.eye(4)
    Q[0, 3] = Q[3, 0] = 0.1
    with pytest.raises(ValueError, match="nonlocal coupling"):
        decompose_local_symmetric_q(Q, edges=[(0, 1), (1, 2), (2, 3)])


def test_self_path_range_exposes_rank_one_diagonal_stamp():
    assert required_self_path_full_scale() == pytest.approx(2.95)


def test_12bit_self_path_matches_8bit_edge_absolute_lsb():
    edge_lsb = 0.25 / signed_midtread_positive_codes(8)
    assert self_bits_matching_edge_lsb(
        edge_bits=8, edge_full_scale=0.25, self_full_scale=3.0
    ) == 12
    self_lsb = 3.0 / signed_midtread_positive_codes(12)
    assert self_lsb <= edge_lsb
    assert bits_for_absolute_lsb(3.0, edge_lsb) == 12


def test_dual_reverse_halves_sequential_reverse_traversal_count():
    assert gradient_traversal_ticks(210, objective_terms=1) == 420
    assert gradient_traversal_ticks(210, objective_terms=2) == 840


def test_parameter_hold_window_is_submillisecond_at_1mhz_for_210_step_contrast():
    hold = gradient_hold_seconds(210, 1_000_000.0, objective_terms=2)
    assert 0.00084 < hold < 0.00085


def test_leakage_recommendation_maps_to_about_one_millisecond_tau_at_1mhz():
    tau = retention_time_constant_seconds(1_000_000.0, 0.001)
    assert tau == pytest.approx(0.0009995, rel=2e-4)


def test_reference_profile_enforces_structural_coherence():
    p = TW1ACircuitProfile()
    p.validate()
    c = p.coherence_contract()
    assert "lane A evolves F+A" in c["reverse_pair"]
    assert "writes inhibited" in c["edge_code_storage"]
    assert p.differential_state_registers == 256
    assert p.scalar_sample_capacitors_minimum == 512
    assert len(p.tick_microphases()) == 8
