/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Pretendard',
          '-apple-system',
          'BlinkMacSystemFont',
          'system-ui',
          'Roboto',
          'Helvetica Neue',
          'Segoe UI',
          'Apple SD Gothic Neo',
          'Noto Sans KR',
          'Malgun Gothic',
          'sans-serif',
        ],
      },
      colors: {
        // Primary: 상호작용 가능한 요소
        primary: {
          DEFAULT: '#3B82F6', // blue-500
          hover: '#2563EB',   // blue-600
          light: '#60A5FA',   // blue-400
        },
        // Secondary: 긍정적 상태 표시
        secondary: {
          DEFAULT: '#22C55E', // green-500
          hover: '#16A34A',   // green-600
          light: '#4ADE80',   // green-400
        },
        // Neutral: 배경, 텍스트
        neutral: {
          bg: '#F1F5F9',      // slate-100
          card: '#FFFFFF',    // white
          text: '#1E293B',    // slate-800
          'text-light': '#64748B', // slate-500
          border: '#CBD5E1',  // slate-300
        },
        // Status
        danger: '#EF4444',    // red-500
        warning: '#F59E0B',   // amber-500
      },
      spacing: {
        sidebar: '280px',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
