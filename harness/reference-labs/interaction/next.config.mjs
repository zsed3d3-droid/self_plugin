import {readFileSync} from 'node:fs';
const gsapNotice=readFileSync(new URL('./licenses/gsap-package-notice.txt',import.meta.url),'utf8');
export default {
 output:'standalone',poweredByHeader:false,generateBuildId:async()=> 'interaction-lab-v1',
 webpack(config,{webpack}){
  // Keep the package's proprietary notice after Next's minimizer; no runtime code is added.
  config.plugins.push(new webpack.BannerPlugin({
   banner:'Third-party notice for GSAP portions; GSAP runtime loads only in its mode. Full direct-package notices: /third-party-notices.txt\n'+gsapNotice,
   test:/\.js$/,stage:webpack.Compilation.PROCESS_ASSETS_STAGE_REPORT
  }));
  return config;
 }
};
