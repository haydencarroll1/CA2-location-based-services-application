/*
 * routing.js - Handles route calculations using OSRM
 * Uses the free public OSRM demo server for routing
 */

const RoutingModule = (function() {
  'use strict';

  const CONFIG = {
    OSRM_BASE_URL: 'https://router.project-osrm.org',
    
    PROFILES: {
      driving: 'driving',
      walking: 'foot',
      cycling: 'bike'
    },
    
    STYLES: {
      driving: { color: '#3b82f6', weight: 5, opacity: 0.8 },
      walking: { color: '#10b981', weight: 4, opacity: 0.8, dashArray: '10, 10' },
      cycling: { color: '#f59e0b', weight: 4, opacity: 0.8 }
    }
  };

  let map = null;
  let routeLayer = null;
  let startMarker = null;
  let endMarker = null;
  let currentRoute = null;

  const startIcon = L.divIcon({
    className: 'route-marker route-marker--start',
    html: `<div style="
      width: 24px; height: 24px; 
      background: linear-gradient(135deg, #10b981, #059669);
      border: 3px solid white;
      border-radius: 50%;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      display: flex; align-items: center; justify-content: center;
      color: white; font-weight: bold; font-size: 12px;
    ">A</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12]
  });

  const endIcon = L.divIcon({
    className: 'route-marker route-marker--end',
    html: `<div style="
      width: 24px; height: 24px; 
      background: linear-gradient(135deg, #ef4444, #dc2626);
      border: 3px solid white;
      border-radius: 50%;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      display: flex; align-items: center; justify-content: center;
      color: white; font-weight: bold; font-size: 12px;
    ">B</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12]
  });

  function init(leafletMap) {
    map = leafletMap;
    routeLayer = L.layerGroup().addTo(map);
    
    console.log('[Routing] Module initialized');
  }

  async function getRoute(start, end, profile = 'walking') {
    const osrmProfile = CONFIG.PROFILES[profile] || CONFIG.PROFILES.walking;
    const coords = `${start.lng},${start.lat};${end.lng},${end.lat}`;
    
    const url = `${CONFIG.OSRM_BASE_URL}/route/v1/${osrmProfile}/${coords}?overview=full&geometries=geojson&steps=true`;
    
    console.log('[Routing] Fetching route:', url);
    
    try {
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`OSRM error: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.code !== 'Ok') {
        throw new Error(`OSRM returned: ${data.code}`);
      }
      
      return data.routes[0];
    } catch (error) {
      console.error('[Routing] Failed to get route:', error);
      throw error;
    }
  }

  async function showRoute(start, end, profile = 'walking') {
    clearRoute();
    
    try {
      const route = await getRoute(start, end, profile);
      currentRoute = route;
      const coordinates = route.geometry.coordinates.map(coord => [coord[1], coord[0]]);
      
      const style = CONFIG.STYLES[profile] || CONFIG.STYLES.walking;
      const routeLine = L.polyline(coordinates, {
        ...style,
        className: 'route-line'
      }).addTo(routeLayer);
      
      addRouteArrows(coordinates, style.color);
      
      startMarker = L.marker(start, { icon: startIcon })
        .bindPopup('<strong>Start</strong>')
        .addTo(routeLayer);
      
      endMarker = L.marker(end, { icon: endIcon })
        .bindPopup(`
          <strong>Destination</strong><br>
          <small>${formatDuration(route.duration)} • ${formatDistance(route.distance)}</small>
        `)
        .addTo(routeLayer);
      
      map.fitBounds(routeLine.getBounds(), { padding: [50, 50] });
      
      return {
        distance: route.distance,
        duration: route.duration,
        distanceText: formatDistance(route.distance),
        durationText: formatDuration(route.duration),
        steps: route.legs[0]?.steps || []
      };
      
    } catch (error) {
      console.error('[Routing] Failed to show route:', error);
      throw error;
    }
  }

  function addRouteArrows(coordinates, color) {
    const step = Math.max(1, Math.floor(coordinates.length / 10));
    
    for (let i = step; i < coordinates.length - 1; i += step) {
      const current = coordinates[i];
      const next = coordinates[i + 1];
      
      const angle = Math.atan2(next[0] - current[0], next[1] - current[1]) * 180 / Math.PI;
      
      const arrowIcon = L.divIcon({
        className: 'route-arrow',
        html: `<div style="
          transform: rotate(${angle}deg);
          color: ${color};
          font-size: 16px;
          text-shadow: 0 1px 2px rgba(0,0,0,0.3);
        ">▲</div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8]
      });
      
      L.marker(current, { icon: arrowIcon, interactive: false }).addTo(routeLayer);
    }
  }

  function clearRoute() {
    routeLayer.clearLayers();
    startMarker = null;
    endMarker = null;
    currentRoute = null;
  }

  function formatDistance(meters) {
    if (meters < 1000) {
      return `${Math.round(meters)} m`;
    }
    return `${(meters / 1000).toFixed(1)} km`;
  }

  function formatDuration(seconds) {
    if (seconds < 60) {
      return `${Math.round(seconds)} sec`;
    }
    if (seconds < 3600) {
      return `${Math.round(seconds / 60)} min`;
    }
    const hours = Math.floor(seconds / 3600);
    const mins = Math.round((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
  }

  function getDirections() {
    if (!currentRoute || !currentRoute.legs) return [];
    
    return currentRoute.legs[0].steps.map(step => ({
      instruction: step.maneuver.type,
      modifier: step.maneuver.modifier,
      distance: formatDistance(step.distance),
      duration: formatDuration(step.duration),
      name: step.name || 'Unnamed road'
    }));
  }

  // export functions
  return {
    init,
    getRoute,
    showRoute,
    clearRoute,
    getDirections,
    formatDistance,
    formatDuration
  };
})();

function initRouting(map) {
  RoutingModule.init(map);
  addRoutingUI(map);
}

async function showRouteToAmenity(from, to, mode = 'walking') {
  try {
    const result = await RoutingModule.showRoute(from, to, mode);
    showRouteInfo(result);
    
    return result;
  } catch (error) {
    console.error('Failed to calculate route:', error);
    alert('Could not calculate route. Please try again.');
  }
}

function addRoutingUI(map) {
  const routingPanel = L.control({ position: 'topright' });
  
  routingPanel.onAdd = function() {
    const div = L.DomUtil.create('div', 'routing-panel');
    div.innerHTML = `
      <style>
        .routing-panel {
          background: rgba(17, 24, 39, 0.9);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 12px;
          padding: 12px;
          min-width: 200px;
          color: white;
          font-family: system-ui, sans-serif;
        }
        .routing-panel__title {
          font-weight: 600;
          margin-bottom: 8px;
          font-size: 14px;
        }
        .routing-panel__modes {
          display: flex;
          gap: 4px;
          margin-bottom: 8px;
        }
        .routing-panel__mode {
          flex: 1;
          padding: 8px;
          border: 1px solid rgba(255,255,255,0.2);
          background: transparent;
          color: white;
          border-radius: 6px;
          cursor: pointer;
          font-size: 16px;
          transition: all 0.2s;
        }
        .routing-panel__mode:hover {
          background: rgba(255,255,255,0.1);
        }
        .routing-panel__mode.active {
          background: #06b6d4;
          border-color: #06b6d4;
        }
        .routing-panel__info {
          font-size: 12px;
          color: #94a3b8;
          margin-top: 8px;
        }
        .routing-panel__clear {
          width: 100%;
          padding: 8px;
          background: rgba(239, 68, 68, 0.2);
          border: 1px solid rgba(239, 68, 68, 0.3);
          color: #fca5a5;
          border-radius: 6px;
          cursor: pointer;
          margin-top: 8px;
          font-size: 12px;
        }
        .routing-panel__clear:hover {
          background: rgba(239, 68, 68, 0.3);
        }
      </style>
      <div class="routing-panel__title">🧭 Directions</div>
      <div class="routing-panel__modes">
        <button class="routing-panel__mode active" data-mode="walking" title="Walking">🚶</button>
        <button class="routing-panel__mode" data-mode="cycling" title="Cycling">🚴</button>
        <button class="routing-panel__mode" data-mode="driving" title="Driving">🚗</button>
      </div>
      <div class="routing-panel__info" id="routeInfo">
        Click an amenity to get directions
      </div>
      <button class="routing-panel__clear" id="clearRouteBtn" style="display: none;">
        ✕ Clear Route
      </button>
    `;
    
    L.DomEvent.disableClickPropagation(div);
    
    return div;
  };
  
  routingPanel.addTo(map);
  
  document.querySelectorAll('.routing-panel__mode').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.routing-panel__mode').forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      window.currentRoutingMode = e.target.dataset.mode;
    });
  });
  
  document.getElementById('clearRouteBtn')?.addEventListener('click', () => {
    RoutingModule.clearRoute();
    document.getElementById('routeInfo').textContent = 'Click an amenity to get directions';
    document.getElementById('clearRouteBtn').style.display = 'none';
  });
  
  window.currentRoutingMode = 'walking';
}

function showRouteInfo(result) {
  const infoDiv = document.getElementById('routeInfo');
  const clearBtn = document.getElementById('clearRouteBtn');
  
  if (infoDiv) {
    infoDiv.innerHTML = `
      <strong>${result.durationText}</strong> • ${result.distanceText}
    `;
  }
  
  if (clearBtn) {
    clearBtn.style.display = 'block';
  }
}
