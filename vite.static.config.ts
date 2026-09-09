import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
export default defineConfig({plugins:[react()],base:process.env.BASE_PATH||'/',resolve:{alias:{'@':path.resolve(import.meta.dirname,'.')}},build:{outDir:'dist',emptyOutDir:true},server:{host:'0.0.0.0',allowedHosts:['terminal.local']}});
