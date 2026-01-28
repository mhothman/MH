import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { getPublicBranding } from '../api/branding';

const ThemeContext = createContext(null);

const DEFAULT_BRANDING = {
  logo_url: null,
  primary_color: '#0f172a',
  secondary_color: '#3b82f6',
  accent_color: '#10b981',
  dark_mode_supported: true,
  organization_name: 'ProFlow',
  heading_font: 'inter',
  heading_font_url: null,
  body_font: 'inter',
  body_font_url: null,
  custom_css: null
};

// Preset font mappings
const FONT_MAP = {
  'inter': { name: 'Inter', url: 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap' },
  'roboto': { name: 'Roboto', url: 'https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap' },
  'poppins': { name: 'Poppins', url: 'https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap' },
  'open-sans': { name: 'Open Sans', url: 'https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;500;600;700&display=swap' },
  'lato': { name: 'Lato', url: 'https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&display=swap' },
  'montserrat': { name: 'Montserrat', url: 'https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap' },
  'nunito': { name: 'Nunito', url: 'https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;500;600;700&display=swap' },
  'raleway': { name: 'Raleway', url: 'https://fonts.googleapis.com/css2?family=Raleway:wght@300;400;500;600;700&display=swap' },
  'source-sans': { name: 'Source Sans Pro', url: 'https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&display=swap' },
  'playfair': { name: 'Playfair Display', url: 'https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&display=swap' },
  'merriweather': { name: 'Merriweather', url: 'https://fonts.googleapis.com/css2?family=Merriweather:wght@300;400;700&display=swap' },
  'dm-sans': { name: 'DM Sans', url: 'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap' },
};

export const ThemeProvider = ({ children }) => {
  // Dark/Light theme
  const [theme, setTheme] = useState(() => {
    const stored = localStorage.getItem('proflow_theme');
    if (stored) return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  // Organization branding
  const [branding, setBranding] = useState(DEFAULT_BRANDING);
  const [brandingLoading, setBrandingLoading] = useState(false);
  
  // Refs for dynamic style elements
  const fontStyleRef = useRef(null);
  const customCssRef = useRef(null);

  // Apply dark/light theme
  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
    localStorage.setItem('proflow_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  // Apply CSS variables for branding colors
  const applyBrandingColors = useCallback((brandingData) => {
    const root = document.documentElement;
    
    root.style.setProperty('--org-primary-color', brandingData.primary_color || DEFAULT_BRANDING.primary_color);
    root.style.setProperty('--org-secondary-color', brandingData.secondary_color || DEFAULT_BRANDING.secondary_color);
    root.style.setProperty('--org-accent-color', brandingData.accent_color || DEFAULT_BRANDING.accent_color);
    
    // Generate lighter/darker variants
    root.style.setProperty('--org-primary-light', adjustColor(brandingData.primary_color || DEFAULT_BRANDING.primary_color, 20));
    root.style.setProperty('--org-primary-dark', adjustColor(brandingData.primary_color || DEFAULT_BRANDING.primary_color, -20));
    root.style.setProperty('--org-secondary-light', adjustColor(brandingData.secondary_color || DEFAULT_BRANDING.secondary_color, 20));
    root.style.setProperty('--org-secondary-dark', adjustColor(brandingData.secondary_color || DEFAULT_BRANDING.secondary_color, -20));
  }, []);

  // Apply fonts
  const applyFonts = useCallback((brandingData) => {
    // Remove existing font style
    if (fontStyleRef.current) {
      fontStyleRef.current.remove();
    }

    const headingFont = brandingData.heading_font || 'inter';
    const bodyFont = brandingData.body_font || 'inter';
    const headingFontUrl = brandingData.heading_font_url;
    const bodyFontUrl = brandingData.body_font_url;

    // Build font imports
    const fontUrls = new Set();
    let headingFontFamily = 'Inter';
    let bodyFontFamily = 'Inter';

    // Heading font
    if (headingFont === 'custom' && headingFontUrl) {
      fontUrls.add(headingFontUrl);
      // Extract font name from URL or use generic
      headingFontFamily = extractFontName(headingFontUrl) || 'CustomHeading';
    } else if (FONT_MAP[headingFont]) {
      fontUrls.add(FONT_MAP[headingFont].url);
      headingFontFamily = FONT_MAP[headingFont].name;
    }

    // Body font
    if (bodyFont === 'custom' && bodyFontUrl) {
      fontUrls.add(bodyFontUrl);
      bodyFontFamily = extractFontName(bodyFontUrl) || 'CustomBody';
    } else if (FONT_MAP[bodyFont]) {
      fontUrls.add(FONT_MAP[bodyFont].url);
      bodyFontFamily = FONT_MAP[bodyFont].name;
    }

    // Create style element with font imports and CSS variables
    const style = document.createElement('style');
    style.id = 'org-fonts';
    
    let cssContent = '';
    fontUrls.forEach(url => {
      cssContent += `@import url('${url}');\n`;
    });
    
    cssContent += `
      :root {
        --org-heading-font: '${headingFontFamily}', sans-serif;
        --org-body-font: '${bodyFontFamily}', sans-serif;
      }
      h1, h2, h3, h4, h5, h6, .font-heading {
        font-family: var(--org-heading-font) !important;
      }
      body, p, span, div, input, textarea, button, .font-body {
        font-family: var(--org-body-font);
      }
    `;
    
    style.textContent = cssContent;
    document.head.appendChild(style);
    fontStyleRef.current = style;
  }, []);

  // Apply custom CSS
  const applyCustomCSS = useCallback((customCss) => {
    // Remove existing custom CSS
    if (customCssRef.current) {
      customCssRef.current.remove();
      customCssRef.current = null;
    }

    if (!customCss) return;

    // Create scoped style element
    const style = document.createElement('style');
    style.id = 'org-custom-css';
    style.textContent = customCss;
    document.head.appendChild(style);
    customCssRef.current = style;
  }, []);

  // Apply all branding
  const applyFullBranding = useCallback((brandingData) => {
    applyBrandingColors(brandingData);
    applyFonts(brandingData);
    applyCustomCSS(brandingData.custom_css);
  }, [applyBrandingColors, applyFonts, applyCustomCSS]);

  // Load branding for organization
  const loadBranding = useCallback(async (orgId) => {
    if (!orgId) {
      setBranding(DEFAULT_BRANDING);
      applyFullBranding(DEFAULT_BRANDING);
      return;
    }

    setBrandingLoading(true);
    try {
      const data = await getPublicBranding(orgId);
      setBranding(data);
      applyFullBranding(data);
    } catch (error) {
      console.error('Failed to load branding:', error);
      setBranding(DEFAULT_BRANDING);
      applyFullBranding(DEFAULT_BRANDING);
    } finally {
      setBrandingLoading(false);
    }
  }, [applyFullBranding]);

  // Reset to default branding
  const resetTheme = useCallback(() => {
    setBranding(DEFAULT_BRANDING);
    applyFullBranding(DEFAULT_BRANDING);
  }, [applyFullBranding]);

  // Preview branding (without saving)
  const previewBranding = useCallback((previewData) => {
    const merged = { ...branding, ...previewData };
    applyFullBranding(merged);
  }, [branding, applyFullBranding]);

  // Revert preview to current saved branding
  const revertPreview = useCallback(() => {
    applyFullBranding(branding);
  }, [branding, applyFullBranding]);

  // Apply branding on initial load
  useEffect(() => {
    applyFullBranding(branding);
  }, []);

  return (
    <ThemeContext.Provider value={{ 
      // Theme (dark/light)
      theme, 
      setTheme, 
      toggleTheme,
      // Branding
      branding,
      brandingLoading,
      loadBranding,
      resetTheme,
      previewBranding,
      revertPreview,
      setBranding
    }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

// Helper function to lighten/darken colors
function adjustColor(hex, percent) {
  if (!hex) return '#000000';
  hex = hex.replace('#', '');
  
  let r = parseInt(hex.substring(0, 2), 16);
  let g = parseInt(hex.substring(2, 4), 16);
  let b = parseInt(hex.substring(4, 6), 16);
  
  r = Math.min(255, Math.max(0, r + (r * percent / 100)));
  g = Math.min(255, Math.max(0, g + (g * percent / 100)));
  b = Math.min(255, Math.max(0, b + (b * percent / 100)));
  
  const toHex = (n) => Math.round(n).toString(16).padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

// Extract font family name from Google Fonts URL
function extractFontName(url) {
  try {
    const match = url.match(/family=([^:&]+)/);
    if (match) {
      return match[1].replace(/\+/g, ' ');
    }
  } catch (e) {
    console.error('Failed to extract font name:', e);
  }
  return null;
}

// Helper to check if color has good contrast
export function hasGoodContrast(color1, color2) {
  const getLuminance = (hex) => {
    hex = hex.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16) / 255;
    const g = parseInt(hex.substring(2, 4), 16) / 255;
    const b = parseInt(hex.substring(4, 6), 16) / 255;
    
    const adjust = (c) => c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b);
  };
  
  const l1 = getLuminance(color1);
  const l2 = getLuminance(color2);
  const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  
  return ratio >= 4.5;
}

// Export font map for use in settings
export const PRESET_FONTS = FONT_MAP;
