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
        // Accent: AI 응답 강조
        accent: {
          DEFAULT: '#818CF8', // indigo-400
          hover: '#6366F1',   // indigo-500
        },
        // Neutral (Dark Mode): 배경, 텍스트
        neutral: {
          bg: '#0A0A0A',      // 거의 검은색 배경
          'bg-secondary': '#171717', // neutral-900
          card: '#262626',    // neutral-800
          'card-hover': '#404040', // neutral-700
          text: '#E5E5E5',    // neutral-200
          'text-light': '#A3A3A3', // neutral-400
          border: '#404040',  // neutral-700
          'border-light': '#525252', // neutral-600
        },
        // Status
        danger: '#EF4444',    // red-500
        warning: '#F59E0B',   // amber-500
        success: '#22C55E',   // green-500
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
