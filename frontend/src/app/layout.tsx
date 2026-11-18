import type { Metadata } from 'next';
import './globals.css';
import 'maplibre-gl/dist/maplibre-gl.css';
import { CITY } from '@/config/city';
export const metadata: Metadata = { title: 'SafePath · Plan your journey', description: `A ${CITY.name} walking-route pilot with transparent safety evidence.` };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
