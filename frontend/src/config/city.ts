import config from './cities.json';
export const CITY = config.cities[config.activeCity as keyof typeof config.cities];
