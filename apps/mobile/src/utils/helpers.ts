import React from 'react';
import { Dimensions } from 'react-native';

export const useResponsive = () => {
  const [dimensions, setDimensions] = React.useState(Dimensions.get('window'));

  React.useEffect(() => {
    const subscription = Dimensions.addEventListener('change', ({ window }) => {
      setDimensions(window);
    });

    return () => subscription?.remove();
  }, []);

  return {
    width: dimensions.width,
    height: dimensions.height,
    isSmall: dimensions.width < 375,
    isMedium: dimensions.width >= 375 && dimensions.width < 500,
    isLarge: dimensions.width >= 500,
  };
};

export const formatDate = (date: Date | string): string => {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (hours < 1) return 'Just now';
  if (hours < 24) return `${hours}h ago`;
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days}d ago`;

  return d.toLocaleDateString();
};

export const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export const getRiskColor = (level: string) => {
  switch (level.toLowerCase()) {
    case 'low':
      return '#5EE1C4';
    case 'medium':
      return '#F4C95D';
    case 'high':
    case 'critical':
      return '#FF5D6C';
    default:
      return '#7DA0CA';
  }
};

export const truncatePhone = (phone: string, visible: number = 4): string => {
  if (phone.length <= visible) return phone;
  return `${phone.slice(0, 3)}...${phone.slice(-visible)}`;
};
