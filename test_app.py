"""
Tests unitarios para Opti-Ruta Sky
pytest - Test Framework
"""

import pytest
import json
from app import app, haversine_distance, find_shortest_tour, optimize_route_wolfram, flight_monitor


@pytest.fixture
def client():
    """Cliente de prueba Flask."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestHaversineDistance:
    """Tests para cálculo de distancia geodésica."""
    
    def test_distance_cdmx_querétaro(self):
        """Distancia CDMX (19.43, -99.13) a Querétaro (20.59, -100.39)."""
        dist = haversine_distance(19.43, -99.13, 20.59, -100.39)
        # Distancia aproximada: ~150 km
        assert 140 < dist < 160
    
    def test_distance_same_point(self):
        """Distancia entre mismo punto debe ser 0."""
        dist = haversine_distance(19.43, -99.13, 19.43, -99.13)
        assert dist == 0
    
    def test_distance_symmetry(self):
        """Distancia debe ser simétrica."""
        dist1 = haversine_distance(19.43, -99.13, 20.59, -100.39)
        dist2 = haversine_distance(20.59, -100.39, 19.43, -99.13)
        assert dist1 == dist2


class TestRouteOptimization:
    """Tests para optimización de rutas."""
    
    def test_single_point_tour(self):
        """Tour con un punto."""
        points = [[19.43, -99.13]]
        dist, route = find_shortest_tour(points)
        assert dist == 0
        assert len(route) == 1
    
    def test_two_point_tour(self):
        """Tour con dos puntos."""
        points = [[19.43, -99.13], [20.59, -100.39]]
        dist, route = find_shortest_tour(points)
        # Distancia debe ser > 0
        assert dist > 0
        assert len(route) == 2
    
    def test_triangle_tour(self):
        """Tour triangular CDMX-Querétaro-Toluca."""
        points = [
            [19.43, -99.13],  # CDMX
            [20.59, -100.39],  # Querétaro
            [18.97, -99.28]    # Toluca
        ]
        dist, route = find_shortest_tour(points)
        assert dist > 0
        assert len(route) == 3


class TestEndpoints:
    """Tests de endpoints HTTP."""
    
    def test_health_endpoint(self, client):
        """GET /health debe retornar 200 OK."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
    
    def test_index_endpoint(self, client):
        """GET / debe retornar dashboard HTML."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'TakeYouOff' in response.data or b'Sky Monitoring' in response.data
    
    def test_vuelos_endpoint(self, client):
        """GET /api/vuelos debe retornar lista de vuelos."""
        response = client.get('/api/vuelos')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert 'vuelos' in data
        assert 'conflictos' in data
        assert 'alerts' in data
    
    def test_statistics_endpoint(self, client):
        """GET /api/statistics debe retornar estadísticas."""
        response = client.get('/api/statistics')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert 'total_flights' in data
        assert 'cargo_flights' in data
    
    def test_optimize_route_invalid_input(self, client):
        """POST /api/optimize-route con entrada inválida."""
        response = client.post('/api/optimize-route',
            json={
                "origen": "invalid",  # Debería ser [lat, lon]
                "destino": [20.0, -99.0]
            })
        assert response.status_code == 400
    
    def test_optimize_route_valid_input(self, client):
        """POST /api/optimize-route con entrada válida en DEV_MOCK."""
        response = client.post('/api/optimize-route',
            json={
                "origen": [19.43, -99.13],
                "destino": [20.59, -100.39],
                "restricciones": []
            },
            headers={"Content-Type": "application/json"})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'ruta_km' in data


class TestFlightMonitor:
    """Tests para el monitor de vuelos."""
    
    def test_flight_monitor_initialization(self):
        """Flight monitor debe inicializarse con vuelos mock."""
        assert len(flight_monitor.flights) > 0
    
    def test_conflict_detection(self):
        """Sistema debe detectar conflictos."""
        conflicts, alerts = flight_monitor.detect_conflicts()
        # Pueden haber o no conflictos dependiendo de la posición de vuelos
        assert isinstance(conflicts, list)
        assert isinstance(alerts, list)
    
    def test_opensky_fetch(self):
        """Fetch OpenSky debe retornar vuelos."""
        flights = flight_monitor.fetch_opensky_data()
        assert len(flights) > 0
        assert all('lat' in f and 'lon' in f for f in flights)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
