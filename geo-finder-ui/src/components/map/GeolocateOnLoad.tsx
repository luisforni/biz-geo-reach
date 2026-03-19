import { useEffect } from "react";
import { useMap } from "react-leaflet";

const ZOOM = 14;
const FALLBACK_CENTER: [number, number] = [40.4168, -3.7038];
const FALLBACK_ZOOM = 12;

export function GeolocateOnLoad() {
  const map = useMap();

  useEffect(() => {
    if (!navigator.geolocation) {
      map.setView(FALLBACK_CENTER, FALLBACK_ZOOM);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        map.setView([pos.coords.latitude, pos.coords.longitude], ZOOM);
      },
      () => {
        map.setView(FALLBACK_CENTER, FALLBACK_ZOOM);
      },
      { timeout: 8000 },
    );
  }, [map]);

  return null;
}
