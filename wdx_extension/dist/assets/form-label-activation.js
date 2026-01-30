/**
 * @license
 * Copyright 2021 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */function r(t){const e=new MouseEvent("click",{bubbles:!0});return t.dispatchEvent(e),e}function s(t){return t.currentTarget!==t.target||t.composedPath()[0]!==t.target||t.target.disabled?!1:!a(t)}function a(t){const e=i;return e&&(t.preventDefault(),t.stopImmediatePropagation()),n(),e}let i=!1;async function n(){i=!0,await null,i=!1}export{r as d,s as i};
