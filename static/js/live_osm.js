const LiveOSM = (function() {
  const OVERPASS_URL = "https://overpass-api.de/api/interpreter";
  const DEFAULT_TIMEOUT = 25;

  // Canonical categories in the UI
  const ALLOWED = ["cafe", "shop", "gym", "atm", "park"];

  // Map OSM tags to our 5 categories
  function normalizeCategory(tags = {}) {
    const amenity = tags.amenity;
    const shop = tags.shop;
    const leisure = tags.leisure;
    const sport = tags.sport;

    // Cafés / food / drink
    if (["cafe", "restaurant", "fast_food", "ice_cream", "pub", "bar"].includes(amenity)) return "cafe";
    // Shops
    if (["convenience", "supermarket", "department_store", "mall"].includes(shop)) return "shop";
    if (amenity === "marketplace") return "shop";
    // Gyms / fitness
    if (["fitness_centre", "gym"].includes(amenity)) return "gym";
    if (sport === "fitness") return "gym";
    // ATMs / banks
    if (amenity === "atm" || amenity === "bank") return "atm";
    // Parks / green
    if (leisure === "park" || leisure === "garden" || leisure === "recreation_ground") return "park";

    return null;
  }

  function buildQuery(lat, lng, km, categories, bounds) {
    const radiusMeters = Math.max(50, Math.min(5000, km * 1000));
    const hasCats = Array.isArray(categories) && categories.length > 0;
    const requested = hasCats ? categories.filter(c => ALLOWED.includes(c)) : ALLOWED;
    const amenityPattern = requested.includes("cafe") || requested.includes("atm") || requested.includes("gym") ? "cafe|restaurant|fast_food|ice_cream|pub|bar|atm|bank|fitness_centre|gym" : "";
    const shopPattern = requested.includes("shop") ? "convenience|supermarket|department_store|mall" : "";
    const leisurePattern = requested.includes("park") ? "park|garden|recreation_ground" : "";

    // If we have map bounds, prefer bbox (south,west,north,east)
    let bboxClause = "";
    if (bounds) {
      bboxClause = `(${bounds.getSouth()},${bounds.getWest()},${bounds.getNorth()},${bounds.getEast()})`;
    }

    const amenitySelector = amenityPattern ? `["amenity"~"${amenityPattern}"]` : "";
    const shopSelector = shopPattern ? `["shop"~"${shopPattern}"]` : "";
    const leisureSelector = leisurePattern ? `["leisure"~"${leisurePattern}"]` : "";

    const selector = bboxClause
      ? `
        node${bboxClause}${amenitySelector};
        node${bboxClause}${shopSelector};
        node${bboxClause}${leisureSelector};
        way${bboxClause}${amenitySelector};
        way${bboxClause}${shopSelector};
        way${bboxClause}${leisureSelector};
        relation${bboxClause}${amenitySelector};
        relation${bboxClause}${shopSelector};
        relation${bboxClause}${leisureSelector};
      `
      : `
        node(around:${radiusMeters},${lat},${lng})${amenitySelector};
        node(around:${radiusMeters},${lat},${lng})${shopSelector};
        node(around:${radiusMeters},${lat},${lng})${leisureSelector};
        way(around:${radiusMeters},${lat},${lng})${amenitySelector};
        way(around:${radiusMeters},${lat},${lng})${shopSelector};
        way(around:${radiusMeters},${lat},${lng})${leisureSelector};
        relation(around:${radiusMeters},${lat},${lng})${amenitySelector};
        relation(around:${radiusMeters},${lat},${lng})${shopSelector};
        relation(around:${radiusMeters},${lat},${lng})${leisureSelector};
      `;

    return `
      [out:json][timeout:${DEFAULT_TIMEOUT}];
      (
        ${selector}
      );
      out center 60;
    `;
  }

  function elementToFeature(el, requestedCats) {
    const center = el.type === "node"
      ? { lat: el.lat, lon: el.lon }
      : el.center;
    if (!center) return null;

    const props = el.tags || {};
    const normalized = normalizeCategory(props);
    if (!normalized) return null;

    // If UI requested specific categories, filter here too
    if (Array.isArray(requestedCats) && requestedCats.length > 0 && !requestedCats.includes(normalized)) {
      return null;
    }

    const name = props.name || "Unnamed";

    return {
      type: "Feature",
      geometry: {
        type: "Point",
        coordinates: [center.lon, center.lat]
      },
      properties: {
        id: el.id,
        name,
        category: normalized,
        addr_street: props["addr:street"] || "",
        operator: props.operator || "",
        cuisine: props.cuisine || "",
        opening_hours: props.opening_hours || "",
        website: props.website || "",
        phone: props.phone || "",
        source: "OSM"
      }
    };
  }

  async function fetchAmenities(lat, lng, km = 1, categories = [], bounds = null) {
    const query = buildQuery(lat, lng, km, categories, bounds);
    const formData = new URLSearchParams();
    formData.set("data", query);

    const resp = await fetch(OVERPASS_URL, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString()
    });

    if (!resp.ok) throw new Error(`Overpass error: ${resp.status}`);
    const data = await resp.json();
    const features = (data.elements || [])
      .map(el => elementToFeature(el, categories))
      .filter(Boolean);
    return features;
  }

  return {
    fetchAmenities
  };
})();
