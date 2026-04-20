This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

Import the GitHub repo and set **Root Directory** to **`frontend`** (required). Copy env vars from **`.env.local.example`** into Vercel (see the repository **README** for `TIKTOK_DIRECT_PYTHON` on serverless). Do not use a root **`vercel.json`** that runs `npm install --prefix frontend` when Root Directory is already **`frontend`**.

The [Vercel Platform](https://vercel.com/new) works with Next.js out of the box. See [Next.js deployment docs](https://nextjs.org/docs/app/building-your-application/deploying) for details.
