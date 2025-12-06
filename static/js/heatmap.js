const HeatmapModule = (function() {
  'use strict';

  // Configuration
  const CONFIG = {
    // Heatmap appearance
    radius: 25,
    blur: 15,
    maxZoom: 17,
    max: 1.0,
    minOpacity: 0.3,
    
    // Gradient colors (from low to high density)
    gradient: {
      0.0: '#0ea5e9',  // Cyan (low)
      0.3: '#06b6d4',  // Cyan
      0.5: '#8b5cf6',  // Purple
      0.7: '#d946ef',  // Pink
      0.9: '#f43f5e',  // Red
      1.0: '#ef4444'   // Red (high)
    }
  };

  // State
  let map = null;
  let heatLayer = null;
  let isVisible = false;
  let amenityData = [];

  /**
   * Initialize heatmap module
   * @param {L.Map} leafletMap - Leaflet map instance
   */
  function init(leafletMap) {
    map = leafletMap;
    
    // Check if Leaflet.heat is loaded
    if (typeof L.heatLayer === 'undefined') {
      console.error('[Heatmap] Leaflet.heat plugin not loaded! Add this to your HTML:');
      console.error('<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>');
      return;
    }
    
    console.log('[Heatmap] Module initialized');
    
    // Add toggle button to map
    addToggleButton();
  }

  /**
   * Set amenity data for heatmap
   * @param {Array} features - GeoJSON features array
   */
  function setData(features) {
    amenityData = features.map(feature => {
      const coords = feature.geometry.coordinates;
      // Format: [lat, lng, intensity]
      // Intensity is optional - defaults to 1
      return [coords[1], coords[0], 1];
    });
    
    console.log(`[Heatmap] Loaded ${amenityData.length} points`);
    
    // Update heatmap if visible
    if (isVisible) {
      updateHeatmap();
    }
  }

  /**
   * Set data from API response
   * @param {Object} geojson - GeoJSON FeatureCollection
   */
  function setDataFromGeoJSON(geojson) {
    if (geojson && geojson.features) {
      setData(geojson.features);
    }
  }

  /**
   * Create or update heatmap layer
   */
  function updateHeatmap() {
    if (!map || amenityData.length === 0) return;
    
    // Remove existing layer
    if (heatLayer) {
      map.removeLayer(heatLayer);
    }
    
    // Create new heatmap layer
    heatLayer = L.heatLayer(amenityData, {
      radius: CONFIG.radius,
      blur: CONFIG.blur,
      maxZoom: CONFIG.maxZoom,
      max: CONFIG.max,
      minOpacity: CONFIG.minOpacity,
      gradient: CONFIG.gradient
    });
    
    heatLayer.addTo(map);
  }

  /**
   * Show heatmap
   */
  function show() {
    if (!isVisible) {
      isVisible = true;
      updateHeatmap();
      updateToggleButton(true);
    }
  }

  /**
   * Hide heatmap
   */
  function hide() {
    if (isVisible) {
      isVisible = false;
      if (heatLayer) {
        map.removeLayer(heatLayer);
      }
      updateToggleButton(false);
    }
  }

  /**
   * Toggle heatmap visibility
   */
  function toggle() {
    if (isVisible) {
      hide();
    } else {
      show();
    }
  }

  /**
   * Add toggle button to map
   */
  function addToggleButton() {
    const control = L.control({ position: 'topright' });
    
    control.onAdd = function() {
      const btn = L.DomUtil.create('button', 'heatmap-toggle');
      btn.id = 'heatmapToggle';
      btn.innerHTML = '🔥';
      btn.title = 'Toggle Heatmap';
      btn.style.cssText = `
        width: 44px;
        height: 44px;
        background: rgba(17, 24, 39, 0.9);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        color: white;
        font-size: 20px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
        margin-bottom: 8px;
      `;
      
      btn.addEventListener('click', toggle);
      btn.addEventListener('mouseenter', () => {
        btn.style.background = 'rgba(17, 24, 39, 1)';
        btn.style.transform = 'scale(1.05)';
      });
      btn.addEventListener('mouseleave', () => {
        btn.style.background = isVisible ? '#ef4444' : 'rgba(17, 24, 39, 0.9)';
        btn.style.transform = 'scale(1)';
      });
      
      L.DomEvent.disableClickPropagation(btn);
      
      return btn;
    };
    
    control.addTo(map);
  }

  /**
   * Update toggle button appearance
   */
  function updateToggleButton(active) {
    const btn = document.getElementById('heatmapToggle');
    if (btn) {
      btn.style.background = active ? '#ef4444' : 'rgba(17, 24, 39, 0.9)';
      btn.style.borderColor = active ? '#ef4444' : 'rgba(255,255,255,0.1)';
    }
  }

  /**
   * Set heatmap options
   * @param {Object} options - Configuration options
   */
  function setOptions(options) {
    Object.assign(CONFIG, options);
    if (isVisible) {
      updateHeatmap();
    }
  }

  // Public API
  return {
    init,
    setData,
    setDataFromGeoJSON,
    show,
    hide,
    toggle,
    setOptions,
    isVisible: () => isVisible
  };
})();

// =============================================================================
// INTEGRATION EXAMPLE
// =============================================================================

const CategoryHeatmaps = {
  gradients: {
    cafe: {
      0.0: '#92400e', 0.5: '#d97706', 1.0: '#fbbf24'  // Brown to Gold
    },
    park: {
      0.0: '#065f46', 0.5: '#059669', 1.0: '#34d399'  // Green
    },
    gym: {
      0.0: '#7c2d12', 0.5: '#dc2626', 1.0: '#f87171'  // Red
    },
    shop: {
      0.0: '#1e3a8a', 0.5: '#2563eb', 1.0: '#60a5fa'  // Blue
    },
    atm: {
      0.0: '#581c87', 0.5: '#9333ea', 1.0: '#c084fc'  // Purple
    }
  },
  
  showForCategory(category, features) {
    const filtered = features.filter(f => f.properties.category === category);
    
    if (this.gradients[category]) {
      HeatmapModule.setOptions({ gradient: this.gradients[category] });
    }
    
    HeatmapModule.setData(filtered);
    HeatmapModule.show();
  }
};
