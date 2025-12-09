/*
 * weather.js - Weather widget using Open-Meteo API
 * Shows current weather conditions on the map
 */

const WeatherModule = (function() {
  'use strict';

  const API_BASE = 'https://api.open-meteo.com/v1/forecast';
  
  // Weather code to icon/description mapping
  const WEATHER_CODES = {
    0: { icon: '☀️', desc: 'Clear sky' },
    1: { icon: '🌤️', desc: 'Mainly clear' },
    2: { icon: '⛅', desc: 'Partly cloudy' },
    3: { icon: '☁️', desc: 'Overcast' },
    45: { icon: '🌫️', desc: 'Foggy' },
    48: { icon: '🌫️', desc: 'Depositing rime fog' },
    51: { icon: '🌧️', desc: 'Light drizzle' },
    53: { icon: '🌧️', desc: 'Moderate drizzle' },
    55: { icon: '🌧️', desc: 'Dense drizzle' },
    61: { icon: '🌧️', desc: 'Slight rain' },
    63: { icon: '🌧️', desc: 'Moderate rain' },
    65: { icon: '🌧️', desc: 'Heavy rain' },
    71: { icon: '🌨️', desc: 'Slight snow' },
    73: { icon: '🌨️', desc: 'Moderate snow' },
    75: { icon: '❄️', desc: 'Heavy snow' },
    80: { icon: '🌦️', desc: 'Rain showers' },
    81: { icon: '🌦️', desc: 'Moderate showers' },
    82: { icon: '⛈️', desc: 'Violent showers' },
    95: { icon: '⛈️', desc: 'Thunderstorm' },
    96: { icon: '⛈️', desc: 'Thunderstorm with hail' },
    99: { icon: '⛈️', desc: 'Thunderstorm with heavy hail' }
  };

  // State
  let map = null;
  let weatherControl = null;
  let currentWeather = null;

  function init(leafletMap) {
    map = leafletMap;
    
    // Add weather widget to map
    addWeatherWidget();
    
    // Get weather for Dublin by default
    fetchWeather(53.3498, -6.2603);
    
    console.log('[Weather] Module initialized');
  }

  async function fetchWeather(lat, lng) {
    const params = new URLSearchParams({
      latitude: lat,
      longitude: lng,
      current: 'temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m',
      timezone: 'Europe/Dublin'
    });
    
    const url = `${API_BASE}?${params}`;
    
    try {
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Weather API error: ${response.status}`);
      }
      
      const data = await response.json();
      currentWeather = parseWeatherData(data);
      
      updateWeatherWidget(currentWeather);
      
      return currentWeather;
      
    } catch (error) {
      console.error('[Weather] Failed to fetch:', error);
      updateWeatherWidget(null, error);
    }
  }

  function parseWeatherData(data) {
    const current = data.current;
    const weatherInfo = WEATHER_CODES[current.weather_code] || { icon: '❓', desc: 'Unknown' };
    
    return {
      temperature: Math.round(current.temperature_2m),
      humidity: current.relative_humidity_2m,
      windSpeed: Math.round(current.wind_speed_10m),
      weatherCode: current.weather_code,
      icon: weatherInfo.icon,
      description: weatherInfo.desc,
      units: {
        temperature: data.current_units?.temperature_2m || '°C',
        windSpeed: data.current_units?.wind_speed_10m || 'km/h'
      }
    };
  }

  function addWeatherWidget() {
    weatherControl = L.control({ position: 'topright' });
    
    weatherControl.onAdd = function() {
      const div = L.DomUtil.create('div', 'weather-widget');
      div.id = 'weatherWidget';
      div.innerHTML = getWidgetHTML(null, true);
      
      // Prevent map interactions
      L.DomEvent.disableClickPropagation(div);
      
      // Click to refresh
      div.addEventListener('click', () => {
        const center = map.getCenter();
        fetchWeather(center.lat, center.lng);
      });
      
      return div;
    };
    
    weatherControl.addTo(map);
    
    // Add styles
    addWidgetStyles();
  }

  function getWidgetHTML(weather, loading = false) {
    if (loading) {
      return `
        <div class="weather-widget__loading">
          <span class="weather-widget__spinner">⏳</span>
          Loading weather...
        </div>
      `;
    }
    
    if (!weather) {
      return `
        <div class="weather-widget__error">
          ⚠️ Weather unavailable
        </div>
      `;
    }
    
    return `
      <div class="weather-widget__icon">${weather.icon}</div>
      <div class="weather-widget__info">
        <div class="weather-widget__temp">${weather.temperature}°C</div>
        <div class="weather-widget__desc">${weather.description}</div>
        <div class="weather-widget__details">
          💨 ${weather.windSpeed} km/h &nbsp;|&nbsp; 💧 ${weather.humidity}%
        </div>
      </div>
    `;
  }

  function updateWeatherWidget(weather, error = null) {
    const widget = document.getElementById('weatherWidget');
    if (widget) {
      widget.innerHTML = getWidgetHTML(weather);
      widget.classList.remove('weather-widget--loading');
      if (error) {
        widget.classList.add('weather-widget--error');
      }
    }
  }

  function addWidgetStyles() {
    if (document.getElementById('weather-widget-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'weather-widget-styles';
    style.textContent = `
      .weather-widget {
        position: relative;
        z-index: 60;
        background: rgba(17, 24, 39, 0.9);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 12px 16px;
        color: white;
        font-family: system-ui, -apple-system, sans-serif;
        display: flex;
        align-items: center;
        gap: 12px;
        cursor: pointer;
        transition: all 0.2s;
        min-width: 180px;
      }
      
      .weather-widget:hover {
        background: rgba(17, 24, 39, 1);
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
      }
      
      .weather-widget__icon {
        font-size: 32px;
        line-height: 1;
      }
      
      .weather-widget__info {
        flex: 1;
      }
      
      .weather-widget__temp {
        font-size: 20px;
        font-weight: 700;
      }
      
      .weather-widget__desc {
        font-size: 12px;
        color: #94a3b8;
        margin-top: 2px;
      }
      
      .weather-widget__details {
        font-size: 11px;
        color: #64748b;
        margin-top: 4px;
      }
      
      .weather-widget__loading,
      .weather-widget__error {
        font-size: 12px;
        color: #94a3b8;
      }
      
      .weather-widget__spinner {
        display: inline-block;
        animation: spin 1s linear infinite;
      }
      
      @keyframes spin {
        to { transform: rotate(360deg); }
      }
      
      .weather-widget--error {
        border-color: rgba(239, 68, 68, 0.3);
      }
    `;
    
    document.head.appendChild(style);
  }

  function getRecommendation() {
    if (!currentWeather) return null;
    
    const { temperature, weatherCode, windSpeed } = currentWeather;
    
    // Good weather for outdoor activities
    if ([0, 1, 2].includes(weatherCode) && temperature >= 10 && windSpeed < 30) {
      return {
        type: 'outdoor',
        message: 'Great weather for outdoor activities! 🌳',
        suggestedCategories: ['park', 'cafe']
      };
    }
    
    // Rainy - suggest indoor
    if ([51, 53, 55, 61, 63, 65, 80, 81, 82].includes(weatherCode)) {
      return {
        type: 'indoor',
        message: 'Rainy weather - consider indoor options ☔',
        suggestedCategories: ['gym', 'shop', 'cafe']
      };
    }
    
    // Cold - suggest warming up
    if (temperature < 5) {
      return {
        type: 'indoor',
        message: 'Quite cold outside - warm up at a café! ☕',
        suggestedCategories: ['cafe', 'gym']
      };
    }
    
    return {
      type: 'any',
      message: 'Moderate conditions for any activity',
      suggestedCategories: null
    };
  }

  function updateForLocation(latlng) {
    fetchWeather(latlng.lat, latlng.lng);
  }

  return {
    init,
    fetchWeather,
    updateForLocation,
    getRecommendation,
    getCurrentWeather: () => currentWeather
  };
})();

function getWeatherRecommendation() {
  return WeatherModule.getRecommendation();
}
