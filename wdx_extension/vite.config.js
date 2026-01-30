import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        popup: resolve(__dirname, 'popup.html'),
        queue: resolve(__dirname, 'queue.html'),
        manifest: resolve(__dirname, 'manifest.json'),
        options: resolve(__dirname, 'options/options.html'),

        // CSS
        src_fonts_css: resolve(__dirname, 'src/css/fonts.css'),
        src_style: resolve(__dirname, 'src/css/style.css'),

        // JS
        src_js_popup: resolve(__dirname, 'src/js/popup.js'),
        src_js_queue: resolve(__dirname, 'src/js/queue.js'),
        src_js_options: resolve(__dirname, 'src/js/options.js'),
        src_js_constants: resolve(__dirname, 'src/js/constants.js'),
        src_js_background: resolve(__dirname, 'src/js/background.js'),

        // Images
        src_img_icon32: resolve(__dirname, 'src/img/icon32.png'),
        src_img_icon48: resolve(__dirname, 'src/img/icon48.png'),
        src_img_icon64: resolve(__dirname, 'src/img/icon64.png'),
        src_img_icon128: resolve(__dirname, 'src/img/icon128.png'),
        src_img_icon256: resolve(__dirname, 'src/img/icon256.png'),
        src_img_icon512: resolve(__dirname, 'src/img/icon512.png'),
        src_img_settings: resolve(__dirname, 'src/img/settings.png'),

        // Fonts (Rubik)
        src_rubik_regular: resolve(__dirname, 'src/fonts/Rubik/Rubik-Regular.ttf'),
        src_rubik_medium: resolve(__dirname, 'src/fonts/Rubik/Rubik-Medium.ttf'),
        src_rubik_medium_italic: resolve(__dirname, 'src/fonts/Rubik/Rubik-MediumItalic.ttf'),
        src_rubik_bold: resolve(__dirname, 'src/fonts/Rubik/Rubik-Bold.ttf'),
        src_rubik_bolditalic: resolve(__dirname, 'src/fonts/Rubik/Rubik-BoldItalic.ttf'),
        src_rubik_semibold: resolve(__dirname, 'src/fonts/Rubik/Rubik-SemiBold.ttf'),
        src_rubik_semibolditalic: resolve(__dirname, 'src/fonts/Rubik/Rubik-SemiBoldItalic.ttf'),
        src_rubik_black: resolve(__dirname, 'src/fonts/Rubik/Rubik-Black.ttf'),
        src_rubik_blackitalic: resolve(__dirname, 'src/fonts/Rubik/Rubik-BlackItalic.ttf'),
        src_rubik_extrabold: resolve(__dirname, 'src/fonts/Rubik/Rubik-ExtraBold.ttf'),
        src_rubik_extrabolditalic: resolve(__dirname, 'src/fonts/Rubik/Rubik-ExtraBoldItalic.ttf'),
        src_rubik_light: resolve(__dirname, 'src/fonts/Rubik/Rubik-Light.ttf'),
        src_rubik_lightitalic: resolve(__dirname, 'src/fonts/Rubik/Rubik-LightItalic.ttf'),
        src_rubik_italic: resolve(__dirname, 'src/fonts/Rubik/Rubik-Italic.ttf'),
        src_rubik_var: resolve(__dirname, 'src/fonts/Rubik/Rubik-VariableFont_wght.ttf'),
        src_rubik_var_italic: resolve(__dirname, 'src/fonts/Rubik/Rubik-Italic-VariableFont_wght.ttf'),
        src_rubik_ofl: resolve(__dirname, 'src/fonts/Rubik/OFL.txt'),
        src_rubik_readme: resolve(__dirname, 'src/fonts/Rubik/README.txt')
      },
      output: {
        entryFileNames: 'assets/[name].js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/[name].[ext]'
      }
    },
    outDir: 'dist',
    emptyOutDir: true
  }
});