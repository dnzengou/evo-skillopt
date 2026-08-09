import { ImageResponse } from '@vercel/og';

export const config = { runtime: 'edge' };

// Dynamic OG image. Params:
//   ?title=... ?subtitle=...  (both optional; defaults for homepage)
// Access via https://clow-tau.vercel.app/api/og — reference in <meta og:image>.
export default function handler(req) {
  const { searchParams } = new URL(req.url);
  const title = (searchParams.get('title') || 'The bots marketplace where bots get smarter.').slice(0, 120);
  const subtitle = (searchParams.get('subtitle') || 'PicoClaw × EvoMetaClaw · Agent economy on $10 hardware').slice(0, 120);

  return new ImageResponse(
    {
      type: 'div',
      props: {
        style: {
          width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
          justifyContent: 'space-between', padding: '80px',
          background: 'linear-gradient(135deg,#0a0a0f 0%,#1a1a26 60%,#2a1a3a 100%)',
          color: '#f0f0f5', fontFamily: 'system-ui,sans-serif',
        },
        children: [
          {
            type: 'div',
            props: {
              style: { display: 'flex', alignItems: 'center', gap: 16, fontSize: 32, fontWeight: 700 },
              children: [{ type: 'span', props: { children: '🦞' } }, { type: 'span', props: { children: 'Clow' } }],
            },
          },
          {
            type: 'div',
            props: {
              style: { display: 'flex', flexDirection: 'column', gap: 24 },
              children: [
                {
                  type: 'div',
                  props: {
                    style: {
                      fontSize: 72, fontWeight: 800, lineHeight: 1.05, letterSpacing: '-0.02em',
                      background: 'linear-gradient(135deg,#ff6b35 0%,#f7c948 60%,#7c3aed 100%)',
                      backgroundClip: 'text', color: 'transparent',
                    },
                    children: title,
                  },
                },
                {
                  type: 'div',
                  props: {
                    style: { fontSize: 28, color: '#a0a0b8', fontWeight: 500 },
                    children: subtitle,
                  },
                },
              ],
            },
          },
          {
            type: 'div',
            props: {
              style: {
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                fontSize: 20, color: '#606075', borderTop: '1px solid #252535', paddingTop: 24,
              },
              children: [
                { type: 'span', props: { children: 'clow-tau.vercel.app' } },
                { type: 'span', props: { children: '@XTech73781 · MIT · Open source' } },
              ],
            },
          },
        ],
      },
    },
    { width: 1200, height: 630 },
  );
}
