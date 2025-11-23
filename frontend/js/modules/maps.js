// Maps widget functionality using Google Maps JavaScript API
let currentMapsWidgetData = null;
let googleMap = null;
let markers = [];
let infoWindow = null;
let mapsApiLoaded = false;
let mapsApiKey = null;
let placesService = null;
let geocoder = null;

// Fetch API key from backend
async function fetchMapsApiKey() {
    if (mapsApiKey) return mapsApiKey;

    try {
        const response = await fetch('/api/config/maps-api-key');
        const data = await response.json();
        if (data.api_key) {
            mapsApiKey = data.api_key;
            return mapsApiKey;
        }
        console.warn('Maps API key not configured');
        return null;
    } catch (error) {
        console.error('Failed to fetch Maps API key:', error);
        return null;
    }
}

// Load Google Maps JavaScript API dynamically
async function loadGoogleMapsApi() {
    if (mapsApiLoaded) return true;
    if (window.google && window.google.maps && window.google.maps.places) {
        mapsApiLoaded = true;
        return true;
    }

    const apiKey = await fetchMapsApiKey();
    if (!apiKey) {
        console.error('No Maps API key available');
        return false;
    }

    return new Promise((resolve) => {
        // Set up error handler for Google Maps API errors
        window.gm_authFailure = () => {
            console.error('Google Maps API authentication failed - check API key and billing');
            mapsApiLoaded = false;
            resolve(false);
        };

        // Create callback function
        window.initGoogleMaps = () => {
            // Verify the API loaded correctly
            if (window.google && window.google.maps) {
                mapsApiLoaded = true;
                console.log('Google Maps API loaded successfully');
                resolve(true);
            } else {
                console.error('Google Maps API did not load properly');
                resolve(false);
            }
        };

        // Check if script already exists
        const existingScript = document.querySelector('script[src*="maps.googleapis.com"]');
        if (existingScript) {
            // API was already attempted, check if it worked
            if (window.google && window.google.maps) {
                mapsApiLoaded = true;
                resolve(true);
            } else {
                resolve(false);
            }
            return;
        }

        // Load the script
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=initGoogleMaps&libraries=places,geometry&v=weekly`;
        script.async = true;
        script.defer = true;
        script.onerror = () => {
            console.error('Failed to load Google Maps API script');
            resolve(false);
        };

        // Timeout fallback
        const timeout = setTimeout(() => {
            if (!mapsApiLoaded) {
                console.error('Google Maps API load timeout');
                resolve(false);
            }
        }, 10000);

        // Clear timeout on success
        const originalCallback = window.initGoogleMaps;
        window.initGoogleMaps = () => {
            clearTimeout(timeout);
            originalCallback();
        };

        document.head.appendChild(script);
    });
}

// Open maps popup
export async function openMapsPopup(widgetData) {
    console.log('Opening maps popup with data:', widgetData);
    currentMapsWidgetData = widgetData;

    const overlay = document.getElementById('mapsPopupOverlay');
    const loading = document.getElementById('mapsLoading');
    const container = document.getElementById('mapsWidgetContainer');

    if (!overlay) {
        console.error('Maps popup overlay not found');
        return;
    }

    // Show overlay
    overlay.style.display = 'flex';
    loading.style.display = 'flex';
    container.innerHTML = '';

    // Prevent body scrolling
    document.body.style.overflow = 'hidden';

    // Load Google Maps API if needed
    const apiLoaded = await loadGoogleMapsApi();

    if (apiLoaded) {
        try {
            // Render the interactive map
            await renderInteractiveMap(widgetData);
        } catch (error) {
            console.error('Error rendering interactive map, falling back to iframe:', error);
            renderFallbackMap(widgetData);
        }
    } else {
        // Fallback to iframe embed
        console.log('Maps API not available, using iframe fallback');
        renderFallbackMap(widgetData);
    }
}

// Close maps popup
function closeMapsPopup() {
    const overlay = document.getElementById('mapsPopupOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }

    // Restore body scrolling
    document.body.style.overflow = '';

    // Clear markers and map
    clearMarkers();
    googleMap = null;
    placesService = null;
    geocoder = null;

    // Clear widget container
    const container = document.getElementById('mapsWidgetContainer');
    if (container) {
        container.innerHTML = '';
    }

    currentMapsWidgetData = null;
}

// Clear all markers from the map
function clearMarkers() {
    markers.forEach(marker => {
        if (marker.setMap) {
            marker.setMap(null);
        }
    });
    markers = [];
}

// Render interactive map using Google Maps JavaScript API
async function renderInteractiveMap(widgetData) {
    console.log('Rendering interactive map with:', widgetData);

    const loading = document.getElementById('mapsLoading');
    const container = document.getElementById('mapsWidgetContainer');

    const places = widgetData?.places || [];
    const coordinates = widgetData?.coordinates || { latitude: 17.473863, longitude: 78.351742 };

    // Create the layout
    container.innerHTML = `
        <div class="maps-interactive-container">
            ${places.length > 0 ? `
                <div class="maps-places-panel">
                    <div class="maps-places-header">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                            <circle cx="12" cy="10" r="3"></circle>
                        </svg>
                        <span>${places.length} Places Found</span>
                    </div>
                    <div class="maps-places-list" id="mapsPlacesList"></div>
                </div>
            ` : ''}
            <div class="maps-canvas-container">
                <div id="googleMapCanvas" class="google-map-canvas"></div>
            </div>
        </div>
    `;

    // Initialize the map
    const mapCenter = { lat: coordinates.latitude, lng: coordinates.longitude };

    googleMap = new google.maps.Map(document.getElementById('googleMapCanvas'), {
        center: mapCenter,
        zoom: places.length > 0 ? 13 : 14,
        mapTypeControl: true,
        mapTypeControlOptions: {
            style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
            position: google.maps.ControlPosition.TOP_RIGHT
        },
        streetViewControl: true,
        fullscreenControl: true,
        zoomControl: true,
        styles: getMapStyles()
    });

    // Initialize services
    placesService = new google.maps.places.PlacesService(googleMap);
    geocoder = new google.maps.Geocoder();

    // Create info window
    infoWindow = new google.maps.InfoWindow();

    // Hide loading after map is ready
    loading.style.display = 'none';

    // Add markers for places
    if (places.length > 0) {
        const bounds = new google.maps.LatLngBounds();
        const placesList = document.getElementById('mapsPlacesList');

        // Process each place and find its location
        for (let index = 0; index < places.length; index++) {
            const place = places[index];

            // Try to get coordinates for this place
            let placeCoords = await findPlaceCoordinates(place, mapCenter);

            if (placeCoords) {
                // Create marker with custom icon
                const marker = createMarker(placeCoords, place.title, index);
                markers.push(marker);
                bounds.extend(placeCoords);

                // Setup marker click handler
                setupMarkerClickHandler(marker, place, index);

                // Add place to list
                if (placesList) {
                    addPlaceToList(placesList, place, placeCoords, marker, index);
                }
            }
        }

        // Fit map to show all markers
        if (markers.length > 0) {
            if (markers.length === 1) {
                googleMap.setCenter(markers[0].getPosition());
                googleMap.setZoom(15);
            } else {
                googleMap.fitBounds(bounds, { padding: 60 });
            }
        }
    } else {
        // Add center marker
        const centerMarker = new google.maps.Marker({
            position: mapCenter,
            map: googleMap,
            animation: google.maps.Animation.DROP
        });
        markers.push(centerMarker);
    }
}

// Find coordinates for a place using various methods
async function findPlaceCoordinates(place, fallbackCenter) {
    // Method 1: Try to extract from URI
    let coords = extractCoordsFromUri(place.uri);
    if (coords) {
        console.log(`Found coords from URI for ${place.title}:`, coords);
        return coords;
    }

    // Method 2: Use place_id with Places API
    if (place.place_id) {
        coords = await getPlaceDetailsById(place.place_id);
        if (coords) {
            console.log(`Found coords from place_id for ${place.title}:`, coords);
            return coords;
        }
    }

    // Method 3: Search for the place by name using Places API
    coords = await searchPlaceByName(place.title, fallbackCenter);
    if (coords) {
        console.log(`Found coords from search for ${place.title}:`, coords);
        return coords;
    }

    // Method 4: Geocode the place name
    coords = await geocodePlaceName(place.title);
    if (coords) {
        console.log(`Found coords from geocoding for ${place.title}:`, coords);
        return coords;
    }

    console.warn(`Could not find coordinates for: ${place.title}`);
    return null;
}

// Get place details by place_id
function getPlaceDetailsById(placeId) {
    return new Promise((resolve) => {
        if (!placesService || !placeId) {
            resolve(null);
            return;
        }

        placesService.getDetails(
            { placeId: placeId, fields: ['geometry'] },
            (result, status) => {
                if (status === google.maps.places.PlacesServiceStatus.OK && result?.geometry?.location) {
                    resolve({
                        lat: result.geometry.location.lat(),
                        lng: result.geometry.location.lng()
                    });
                } else {
                    resolve(null);
                }
            }
        );
    });
}

// Search for a place by name
function searchPlaceByName(placeName, nearLocation) {
    return new Promise((resolve) => {
        if (!placesService || !placeName) {
            resolve(null);
            return;
        }

        const request = {
            query: placeName,
            location: new google.maps.LatLng(nearLocation.lat, nearLocation.lng),
            radius: 50000 // 50km radius
        };

        placesService.textSearch(request, (results, status) => {
            if (status === google.maps.places.PlacesServiceStatus.OK && results && results.length > 0) {
                const location = results[0].geometry.location;
                resolve({
                    lat: location.lat(),
                    lng: location.lng()
                });
            } else {
                resolve(null);
            }
        });
    });
}

// Geocode a place name to coordinates
function geocodePlaceName(placeName) {
    return new Promise((resolve) => {
        if (!geocoder || !placeName) {
            resolve(null);
            return;
        }

        geocoder.geocode({ address: placeName }, (results, status) => {
            if (status === google.maps.GeocoderStatus.OK && results && results.length > 0) {
                const location = results[0].geometry.location;
                resolve({
                    lat: location.lat(),
                    lng: location.lng()
                });
            } else {
                resolve(null);
            }
        });
    });
}

// Create a marker with custom styling
function createMarker(position, title, index) {
    const marker = new google.maps.Marker({
        position: position,
        map: googleMap,
        title: title,
        label: {
            text: String(index + 1),
            color: 'white',
            fontWeight: 'bold',
            fontSize: '12px'
        },
        icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 18,
            fillColor: '#ea4335',
            fillOpacity: 1,
            strokeColor: '#ffffff',
            strokeWeight: 2,
            labelOrigin: new google.maps.Point(0, 0)
        },
        animation: google.maps.Animation.DROP
    });

    return marker;
}

// Setup click handler for a marker
function setupMarkerClickHandler(marker, place, index) {
    const infoContent = `
        <div class="map-info-window">
            <h4>${place.title}</h4>
            <a href="${place.uri}" target="_blank" rel="noopener noreferrer" class="info-window-link">
                View on Google Maps
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                    <polyline points="15 3 21 3 21 9"></polyline>
                    <line x1="10" y1="14" x2="21" y2="3"></line>
                </svg>
            </a>
        </div>
    `;

    marker.addListener('click', () => {
        infoWindow.setContent(infoContent);
        infoWindow.open(googleMap, marker);
        highlightPlaceItem(index);
    });
}

// Add a place to the list panel
function addPlaceToList(placesList, place, placeCoords, marker, index) {
    const placeItem = document.createElement('div');
    placeItem.className = 'maps-place-card';
    placeItem.dataset.index = index;
    placeItem.innerHTML = `
        <div class="place-marker-badge">${index + 1}</div>
        <div class="place-card-content">
            <div class="place-card-title">${place.title}</div>
            <a href="${place.uri}" target="_blank" rel="noopener noreferrer" class="place-card-link" onclick="event.stopPropagation()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                    <polyline points="15 3 21 3 21 9"></polyline>
                    <line x1="10" y1="14" x2="21" y2="3"></line>
                </svg>
                Open in Maps
            </a>
        </div>
    `;

    // Click to focus on marker
    placeItem.addEventListener('click', () => {
        googleMap.panTo(placeCoords);
        googleMap.setZoom(16);

        const infoContent = `
            <div class="map-info-window">
                <h4>${place.title}</h4>
                <a href="${place.uri}" target="_blank" rel="noopener noreferrer" class="info-window-link">
                    View on Google Maps
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                        <polyline points="15 3 21 3 21 9"></polyline>
                        <line x1="10" y1="14" x2="21" y2="3"></line>
                    </svg>
                </a>
            </div>
        `;

        infoWindow.setContent(infoContent);
        infoWindow.open(googleMap, marker);
        highlightPlaceItem(index);
        marker.setAnimation(google.maps.Animation.BOUNCE);
        setTimeout(() => marker.setAnimation(null), 750);
    });

    placesList.appendChild(placeItem);
}

// Extract coordinates from Google Maps URI
function extractCoordsFromUri(uri) {
    if (!uri) return null;

    // Try various Google Maps URL formats

    // Format: @17.4,78.5,15z
    const atMatch = uri.match(/@(-?\d+\.?\d*),(-?\d+\.?\d*)/);
    if (atMatch) {
        return { lat: parseFloat(atMatch[1]), lng: parseFloat(atMatch[2]) };
    }

    // Format: ?q=17.4,78.5 or &ll=17.4,78.5
    const qMatch = uri.match(/[?&](?:q|ll)=(-?\d+\.?\d*),(-?\d+\.?\d*)/);
    if (qMatch) {
        return { lat: parseFloat(qMatch[1]), lng: parseFloat(qMatch[2]) };
    }

    // Format: /place/17.4,78.5
    const placeMatch = uri.match(/\/place\/(-?\d+\.?\d*),(-?\d+\.?\d*)/);
    if (placeMatch) {
        return { lat: parseFloat(placeMatch[1]), lng: parseFloat(placeMatch[2]) };
    }

    // Format: !3d17.4!4d78.5 (data parameter format)
    const dataMatch = uri.match(/!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)/);
    if (dataMatch) {
        return { lat: parseFloat(dataMatch[1]), lng: parseFloat(dataMatch[2]) };
    }

    return null;
}

// Highlight selected place in the list
function highlightPlaceItem(index) {
    const items = document.querySelectorAll('.maps-place-card');
    items.forEach((item, i) => {
        if (i === index) {
            item.classList.add('active');
            item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            item.classList.remove('active');
        }
    });
}

// Get map styles based on theme
function getMapStyles() {
    const isDarkTheme = document.documentElement.getAttribute('data-theme') === 'dark';

    if (isDarkTheme) {
        return [
            { elementType: 'geometry', stylers: [{ color: '#242f3e' }] },
            { elementType: 'labels.text.stroke', stylers: [{ color: '#242f3e' }] },
            { elementType: 'labels.text.fill', stylers: [{ color: '#746855' }] },
            { featureType: 'administrative.locality', elementType: 'labels.text.fill', stylers: [{ color: '#d59563' }] },
            { featureType: 'poi', elementType: 'labels.text.fill', stylers: [{ color: '#d59563' }] },
            { featureType: 'poi.park', elementType: 'geometry', stylers: [{ color: '#263c3f' }] },
            { featureType: 'poi.park', elementType: 'labels.text.fill', stylers: [{ color: '#6b9a76' }] },
            { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#38414e' }] },
            { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#212a37' }] },
            { featureType: 'road', elementType: 'labels.text.fill', stylers: [{ color: '#9ca5b3' }] },
            { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#746855' }] },
            { featureType: 'road.highway', elementType: 'geometry.stroke', stylers: [{ color: '#1f2835' }] },
            { featureType: 'road.highway', elementType: 'labels.text.fill', stylers: [{ color: '#f3d19c' }] },
            { featureType: 'transit', elementType: 'geometry', stylers: [{ color: '#2f3948' }] },
            { featureType: 'transit.station', elementType: 'labels.text.fill', stylers: [{ color: '#d59563' }] },
            { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#17263c' }] },
            { featureType: 'water', elementType: 'labels.text.fill', stylers: [{ color: '#515c6d' }] },
            { featureType: 'water', elementType: 'labels.text.stroke', stylers: [{ color: '#17263c' }] }
        ];
    }

    return []; // Default light theme
}

// Fallback to iframe embed when API is not available
function renderFallbackMap(widgetData) {
    console.log('Rendering fallback map (iframe embed)');

    const loading = document.getElementById('mapsLoading');
    const container = document.getElementById('mapsWidgetContainer');

    loading.style.display = 'none';

    const places = widgetData?.places || [];
    const coordinates = widgetData?.coordinates || { latitude: 17.473863, longitude: 78.351742 };

    // Helper to get map embed URL for a place
    const getMapEmbedUrl = (placeIndex) => {
        if (placeIndex >= 0 && placeIndex < places.length) {
            const place = places[placeIndex];
            if (place && place.title) {
                const searchQuery = encodeURIComponent(place.title);
                return `https://www.google.com/maps?q=${searchQuery}&z=15&output=embed`;
            }
        }
        return `https://www.google.com/maps?q=${coordinates.latitude},${coordinates.longitude}&z=14&output=embed`;
    };

    if (places.length > 0) {
        let placesHtml = `
            <div class="maps-places-container">
                <div class="maps-places-list">
                    <h3 style="color: var(--text-primary, #e9edef); margin-bottom: 16px; font-size: 16px;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 8px;">
                            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                            <circle cx="12" cy="10" r="3"></circle>
                        </svg>
                        ${places.length} Places Found
                    </h3>
                    <p style="color: var(--text-secondary, #8696a0); font-size: 12px; margin-bottom: 12px;">
                        Click a place to view on map
                    </p>
        `;

        places.forEach((place, index) => {
            placesHtml += `
                <div class="maps-place-item fallback-place-item ${index === 0 ? 'active' : ''}" data-place-index="${index}" style="cursor: pointer;">
                    <div class="place-index">${index + 1}</div>
                    <div class="place-info">
                        <div class="place-title">${place.title}</div>
                        <a href="${place.uri}" target="_blank" rel="noopener noreferrer" class="place-link" onclick="event.stopPropagation()">Open in Google Maps</a>
                    </div>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="place-arrow">
                        <path d="M7 17L17 7M17 7H7M17 7V17"></path>
                    </svg>
                </div>
            `;
        });

        placesHtml += `
                </div>
                <div class="maps-embed-container">
                    <iframe
                        id="mapsEmbedIframe"
                        width="100%"
                        height="100%"
                        style="border:0; border-radius: 8px;"
                        loading="lazy"
                        allowfullscreen
                        referrerpolicy="no-referrer-when-downgrade"
                        src="${getMapEmbedUrl(0)}">
                    </iframe>
                </div>
            </div>
        `;

        container.innerHTML = placesHtml;

        // Add click handlers to place items
        const placeItems = container.querySelectorAll('.fallback-place-item');
        placeItems.forEach((item) => {
            item.addEventListener('click', () => {
                const placeIndex = parseInt(item.dataset.placeIndex, 10);

                // Update active state
                placeItems.forEach(p => p.classList.remove('active'));
                item.classList.add('active');

                // Update iframe to show selected place
                const iframe = document.getElementById('mapsEmbedIframe');
                if (iframe) {
                    iframe.src = getMapEmbedUrl(placeIndex);
                }
            });
        });
    } else if (coordinates) {
        container.innerHTML = `
            <iframe
                width="100%"
                height="100%"
                style="border:0;"
                loading="lazy"
                allowfullscreen
                referrerpolicy="no-referrer-when-downgrade"
                src="https://www.google.com/maps?q=${coordinates.latitude},${coordinates.longitude}&z=14&output=embed">
            </iframe>
        `;
    } else {
        container.innerHTML = '<div style="padding: 20px; text-align: center;">No map data available</div>';
    }
}

// Initialize maps popup close button
export function initializeMapsPopup() {
    const closeBtn = document.getElementById('mapsPopupClose');
    const backdrop = document.querySelector('.maps-popup-backdrop');

    if (closeBtn) {
        closeBtn.addEventListener('click', closeMapsPopup);
    }

    if (backdrop) {
        backdrop.addEventListener('click', closeMapsPopup);
    }

    // Preload the API key
    fetchMapsApiKey();
}
