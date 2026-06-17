# Project Setup and Dependencies

This document provides instructions on how to set up the project and the list of downloaded dependencies to reproduce the environment.

## Frameworks and Libraries Downloaded
1. **Next.js (App Router)**: Initialized via `npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm`
2. **shadcn/ui**: Initialized via `npx shadcn@latest init -d`
3. **Tailwind CSS**: Installed along with Next.js and used for styling.
4. **TypeScript**: Installed along with Next.js for static typing.
5. **lucide-react**: Installed via `npm install lucide-react` for SVG icons used in the UI.

## File Structure Provided
- `src/components/ui/textarea.tsx`: The generic shadcn-like Textarea component.
- `src/components/ui/v0-ai-chat.tsx`: The main `VercelV0Chat` UI component containing auto-resize hooks and state management.
- `src/components/demo.tsx`: The demo wrapper that renders the `VercelV0Chat` component.

## Commands for Others to Download/Reproduce
To set up this exact environment, run the following commands sequentially:

```bash
# 1. Initialize the Next.js app
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --yes

# 2. Enter the directory
cd frontend

# 3. Initialize shadcn/ui defaults
npx shadcn@latest init -d

# 4. Install lucide-react for icons
npm install lucide-react
```
