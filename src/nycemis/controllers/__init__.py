"""Controller registry: build a controller from its name and parameters, loading models before the run."""

from __future__ import annotations

from nycemis.controllers.base import Controller
from nycemis.controllers.eco_ml import EcoMLController, ToyForecaster
from nycemis.controllers.eco_reactive import EcoReactiveController
from nycemis.controllers.legacy_ml import LegacyMLController
from nycemis.controllers.random_reroute import RandomRerouteController
from nycemis.controllers.static import StaticController
from nycemis.controllers.tt_adaptive import TTAdaptiveController
from nycemis.features.builder import feature_names

CONTROLLERS = {
    "static": StaticController,
    "tt_adaptive": TTAdaptiveController,
    "random_reroute": RandomRerouteController,
    "eco_reactive": EcoReactiveController,
    "eco_ml": EcoMLController,
    "legacy_ml": LegacyMLController,
}


class ToyLegacyPredictor:
    """Test stand-in for the legacy RF: NOx rate proportional to the CO2 rate."""

    def predict(self, x):
        return 0.003 * x[:, 0]


def make_controller(name: str, params: dict, scenario: str) -> Controller:
    if name not in CONTROLLERS:
        raise ValueError(f"unknown controller {name!r}; known: {sorted(CONTROLLERS)}")
    params = dict(params)
    if name == "eco_ml":
        model_id = params.get("model_id")
        if model_id == "toy":
            forecaster = ToyForecaster(feature_names("F1"))
        else:
            from nycemis.models.registry import load_forecaster

            forecaster = load_forecaster(scenario, model_id)
        return EcoMLController(params, forecaster=forecaster)
    if name == "legacy_ml":
        model_id = params.get("model_id")
        if model_id == "toy":
            predictor = ToyLegacyPredictor()
        else:
            from nycemis.models.registry import load_legacy_rf

            predictor = load_legacy_rf(scenario, model_id)
        return LegacyMLController(params, predictor=predictor)
    return CONTROLLERS[name](params)
