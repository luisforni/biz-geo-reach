import { MapContainer, TileLayer } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { DrawingTool } from "./DrawingTool";
import { CommerceMarkerLayer } from "./CommerceMarkerLayer";
import { NeighborhoodPolygon } from "./NeighborhoodPolygon";
import { GeolocateOnLoad } from "./GeolocateOnLoad";
import { useCommerceSearch } from "@/hooks/useCommerceSearch";

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const DEFAULT_CENTER: [number, number] = [0, 0];
const DEFAULT_ZOOM = 3;

export function MapCanvas() {
  useCommerceSearch();

  return (
    <MapContainer
      center={DEFAULT_CENTER}
      zoom={DEFAULT_ZOOM}
      style={{ height: "100%", width: "100%" }}
      zoomControl
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        maxZoom={19}
      />
      <GeolocateOnLoad />
      <DrawingTool />
      <CommerceMarkerLayer />
      <NeighborhoodPolygon />
    </MapContainer>
  );
}
