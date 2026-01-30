import{o as O,i as A,u as U}from"./icon-button.js";import{d as _,_ as r,b as x,x as y,c as k,t as L,n as b,r as Q,e as G,E as f,a as V}from"./element-internals.js";/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */let W;function j(i){return(t,e)=>_(t,e,{get(){return(this.renderRoot??W??(W=document.createDocumentFragment())).querySelectorAll(i)}})}/**
 * @license
 * Copyright 2023 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */function D(i,t=p){const e=M(i,t);return e&&(e.tabIndex=0,e.focus()),e}function P(i,t=p){const e=X(i,t);return e&&(e.tabIndex=0,e.focus()),e}function E(i,t=p){for(let e=0;e<i.length;e++){const s=i[e];if(s.tabIndex===0&&t(s))return{item:s,index:e}}return null}function M(i,t=p){for(const e of i)if(t(e))return e;return null}function X(i,t=p){for(let e=i.length-1;e>=0;e--){const s=i[e];if(t(s))return s}return null}function Y(i,t,e=p,s=!0){for(let o=1;o<i.length;o++){const n=(o+t)%i.length;if(n<t&&!s)return null;const a=i[n];if(e(a))return a}return i[t]?i[t]:null}function J(i,t,e=p,s=!0){for(let o=1;o<i.length;o++){const n=(t-o+i.length)%i.length;if(n>t&&!s)return null;const a=i[n];if(e(a))return a}return i[t]?i[t]:null}function S(i,t,e=p,s=!0){if(t){const o=Y(i,t.index,e,s);return o&&(o.tabIndex=0,o.focus()),o}else return D(i,e)}function B(i,t,e=p,s=!0){if(t){const o=J(i,t.index,e,s);return o&&(o.tabIndex=0,o.focus()),o}else return P(i,e)}function Z(){return new Event("request-activation",{bubbles:!0,composed:!0})}function p(i){return!i.disabled}/**
 * @license
 * Copyright 2023 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */const h={ArrowDown:"ArrowDown",ArrowLeft:"ArrowLeft",ArrowUp:"ArrowUp",ArrowRight:"ArrowRight",Home:"Home",End:"End"};class tt{constructor(t){this.handleKeydown=d=>{const l=d.key;if(d.defaultPrevented||!this.isNavigableKey(l))return;const m=this.items;if(!m.length)return;const c=E(m,this.isActivatable);d.preventDefault();const w=this.isRtl(),q=w?h.ArrowRight:h.ArrowLeft,H=w?h.ArrowLeft:h.ArrowRight;let v=null;switch(l){case h.ArrowDown:case H:v=S(m,c,this.isActivatable,this.wrapNavigation());break;case h.ArrowUp:case q:v=B(m,c,this.isActivatable,this.wrapNavigation());break;case h.Home:v=D(m,this.isActivatable);break;case h.End:v=P(m,this.isActivatable);break}v&&c&&c.item!==v&&(c.item.tabIndex=-1)},this.onDeactivateItems=()=>{const d=this.items;for(const l of d)this.deactivateItem(l)},this.onRequestActivation=d=>{this.onDeactivateItems();const l=d.target;this.activateItem(l),l.focus()},this.onSlotchange=()=>{const d=this.items;let l=!1;for(const c of d){if(!c.disabled&&c.tabIndex>-1&&!l){l=!0,c.tabIndex=0;continue}c.tabIndex=-1}if(l)return;const m=M(d,this.isActivatable);m&&(m.tabIndex=0)};const{isItem:e,getPossibleItems:s,isRtl:o,deactivateItem:n,activateItem:a,isNavigableKey:g,isActivatable:I,wrapNavigation:K}=t;this.isItem=e,this.getPossibleItems=s,this.isRtl=o,this.deactivateItem=n,this.activateItem=a,this.isNavigableKey=g,this.isActivatable=I,this.wrapNavigation=K??(()=>!0)}get items(){const t=this.getPossibleItems(),e=[];for(const s of t){if(this.isItem(s)){e.push(s);continue}const n=s.item;n&&this.isItem(n)&&e.push(n)}return e}activateNextItem(){const t=this.items,e=E(t,this.isActivatable);return e&&(e.item.tabIndex=-1),S(t,e,this.isActivatable,this.wrapNavigation())}activatePreviousItem(){const t=this.items,e=E(t,this.isActivatable);return e&&(e.item.tabIndex=-1),B(t,e,this.isActivatable,this.wrapNavigation())}}/**
 * @license
 * Copyright 2021 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */const et=new Set(Object.values(h));class F extends x{get items(){return this.listController.items}constructor(){super(),this.listController=new tt({isItem:t=>t.hasAttribute("md-list-item"),getPossibleItems:()=>this.slotItems,isRtl:()=>getComputedStyle(this).direction==="rtl",deactivateItem:t=>{t.tabIndex=-1},activateItem:t=>{t.tabIndex=0},isNavigableKey:t=>et.has(t),isActivatable:t=>!t.disabled&&t.type!=="text"}),this.internals=this.attachInternals(),this.internals.role="list",this.addEventListener("keydown",this.listController.handleKeydown)}render(){return y`
      <slot
        @deactivate-items=${this.listController.onDeactivateItems}
        @request-activation=${this.listController.onRequestActivation}
        @slotchange=${this.listController.onSlotchange}>
      </slot>
    `}activateNextItem(){return this.listController.activateNextItem()}activatePreviousItem(){return this.listController.activatePreviousItem()}}r([O({flatten:!0})],F.prototype,"slotItems",void 0);/**
 * @license
 * Copyright 2024 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */const it=k`:host{background:var(--md-list-container-color, var(--md-sys-color-surface, #fef7ff));color:unset;display:flex;flex-direction:column;outline:none;padding:8px 0;position:relative}
`;/**
 * @license
 * Copyright 2021 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */let R=class extends F{};R.styles=[it];R=r([L("md-list")],R);/**
 * @license
 * Copyright 2023 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */class N extends x{constructor(){super(...arguments),this.multiline=!1}render(){return y`
      <slot name="container"></slot>
      <slot class="non-text" name="start"></slot>
      <div class="text">
        <slot name="overline" @slotchange=${this.handleTextSlotChange}></slot>
        <slot
          class="default-slot"
          @slotchange=${this.handleTextSlotChange}></slot>
        <slot name="headline" @slotchange=${this.handleTextSlotChange}></slot>
        <slot
          name="supporting-text"
          @slotchange=${this.handleTextSlotChange}></slot>
      </div>
      <slot class="non-text" name="trailing-supporting-text"></slot>
      <slot class="non-text" name="end"></slot>
    `}handleTextSlotChange(){let t=!1,e=0;for(const s of this.textSlots)if(st(s)&&(e+=1),e>1){t=!0;break}this.multiline=t}}r([b({type:Boolean,reflect:!0})],N.prototype,"multiline",void 0);r([j(".text slot")],N.prototype,"textSlots",void 0);function st(i){var t;for(const e of i.assignedNodes({flatten:!0})){const s=e.nodeType===Node.ELEMENT_NODE,o=e.nodeType===Node.TEXT_NODE&&((t=e.textContent)==null?void 0:t.match(/\S/));if(s||o)return!0}return!1}/**
 * @license
 * Copyright 2024 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */const ot=k`:host{color:var(--md-sys-color-on-surface, #1d1b20);font-family:var(--md-sys-typescale-body-large-font, var(--md-ref-typeface-plain, Roboto));font-size:var(--md-sys-typescale-body-large-size, 1rem);font-weight:var(--md-sys-typescale-body-large-weight, var(--md-ref-typeface-weight-regular, 400));line-height:var(--md-sys-typescale-body-large-line-height, 1.5rem);align-items:center;box-sizing:border-box;display:flex;gap:16px;min-height:56px;overflow:hidden;padding:12px 16px;position:relative;text-overflow:ellipsis}:host([multiline]){min-height:72px}[name=overline]{color:var(--md-sys-color-on-surface-variant, #49454f);font-family:var(--md-sys-typescale-label-small-font, var(--md-ref-typeface-plain, Roboto));font-size:var(--md-sys-typescale-label-small-size, 0.6875rem);font-weight:var(--md-sys-typescale-label-small-weight, var(--md-ref-typeface-weight-medium, 500));line-height:var(--md-sys-typescale-label-small-line-height, 1rem)}[name=supporting-text]{color:var(--md-sys-color-on-surface-variant, #49454f);font-family:var(--md-sys-typescale-body-medium-font, var(--md-ref-typeface-plain, Roboto));font-size:var(--md-sys-typescale-body-medium-size, 0.875rem);font-weight:var(--md-sys-typescale-body-medium-weight, var(--md-ref-typeface-weight-regular, 400));line-height:var(--md-sys-typescale-body-medium-line-height, 1.25rem)}[name=trailing-supporting-text]{color:var(--md-sys-color-on-surface-variant, #49454f);font-family:var(--md-sys-typescale-label-small-font, var(--md-ref-typeface-plain, Roboto));font-size:var(--md-sys-typescale-label-small-size, 0.6875rem);font-weight:var(--md-sys-typescale-label-small-weight, var(--md-ref-typeface-weight-medium, 500));line-height:var(--md-sys-typescale-label-small-line-height, 1rem)}[name=container]::slotted(*){inset:0;position:absolute}.default-slot{display:inline}.default-slot,.text ::slotted(*){overflow:hidden;text-overflow:ellipsis}.text{display:flex;flex:1;flex-direction:column;overflow:hidden}
`;/**
 * @license
 * Copyright 2023 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */let C=class extends N{};C.styles=[ot];C=r([L("md-item")],C);/**
 * @license
 * Copyright 2022 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */class u extends x{constructor(){super(...arguments),this.disabled=!1,this.type="text",this.isListItem=!0,this.href="",this.target=""}get isDisabled(){return this.disabled&&this.type!=="link"}willUpdate(t){this.href&&(this.type="link"),super.willUpdate(t)}render(){return this.renderListItem(y`
      <md-item>
        <div slot="container">
          ${this.renderRipple()} ${this.renderFocusRing()}
        </div>
        <slot name="start" slot="start"></slot>
        <slot name="end" slot="end"></slot>
        ${this.renderBody()}
      </md-item>
    `)}renderListItem(t){const e=this.type==="link";let s;switch(this.type){case"link":s=A`a`;break;case"button":s=A`button`;break;default:case"text":s=A`li`;break}const o=this.type!=="text",n=e&&this.target?this.target:f;return U`
      <${s}
        id="item"
        tabindex="${this.isDisabled||!o?-1:0}"
        ?disabled=${this.isDisabled}
        role="listitem"
        aria-selected=${this.ariaSelected||f}
        aria-checked=${this.ariaChecked||f}
        aria-expanded=${this.ariaExpanded||f}
        aria-haspopup=${this.ariaHasPopup||f}
        class="list-item ${V(this.getRenderClasses())}"
        href=${this.href||f}
        target=${n}
        @focus=${this.onFocus}
      >${t}</${s}>
    `}renderRipple(){return this.type==="text"?f:y` <md-ripple
      part="ripple"
      for="item"
      ?disabled=${this.isDisabled}></md-ripple>`}renderFocusRing(){return this.type==="text"?f:y` <md-focus-ring
      @visibility-changed=${this.onFocusRingVisibilityChanged}
      part="focus-ring"
      for="item"
      inward></md-focus-ring>`}onFocusRingVisibilityChanged(t){}getRenderClasses(){return{disabled:this.isDisabled}}renderBody(){return y`
      <slot></slot>
      <slot name="overline" slot="overline"></slot>
      <slot name="headline" slot="headline"></slot>
      <slot name="supporting-text" slot="supporting-text"></slot>
      <slot
        name="trailing-supporting-text"
        slot="trailing-supporting-text"></slot>
    `}onFocus(){this.tabIndex===-1&&this.dispatchEvent(Z())}focus(){var t;(t=this.listItemRoot)==null||t.focus()}}Q(u);u.shadowRootOptions={...x.shadowRootOptions,delegatesFocus:!0};r([b({type:Boolean,reflect:!0})],u.prototype,"disabled",void 0);r([b({reflect:!0})],u.prototype,"type",void 0);r([b({type:Boolean,attribute:"md-list-item",reflect:!0})],u.prototype,"isListItem",void 0);r([b()],u.prototype,"href",void 0);r([b()],u.prototype,"target",void 0);r([G(".list-item")],u.prototype,"listItemRoot",void 0);/**
 * @license
 * Copyright 2024 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */const nt=k`:host{display:flex;-webkit-tap-highlight-color:rgba(0,0,0,0);--md-ripple-hover-color: var(--md-list-item-hover-state-layer-color, var(--md-sys-color-on-surface, #1d1b20));--md-ripple-hover-opacity: var(--md-list-item-hover-state-layer-opacity, 0.08);--md-ripple-pressed-color: var(--md-list-item-pressed-state-layer-color, var(--md-sys-color-on-surface, #1d1b20));--md-ripple-pressed-opacity: var(--md-list-item-pressed-state-layer-opacity, 0.12)}:host(:is([type=button]:not([disabled]),[type=link])){cursor:pointer}md-focus-ring{z-index:1;--md-focus-ring-shape: 8px}a,button,li{background:none;border:none;cursor:inherit;padding:0;margin:0;text-align:unset;text-decoration:none}.list-item{border-radius:inherit;display:flex;flex:1;max-width:inherit;min-width:inherit;outline:none;-webkit-tap-highlight-color:rgba(0,0,0,0);width:100%}.list-item.interactive{cursor:pointer}.list-item.disabled{opacity:var(--md-list-item-disabled-opacity, 0.3);pointer-events:none}[slot=container]{pointer-events:none}md-ripple{border-radius:inherit}md-item{border-radius:inherit;flex:1;height:100%;color:var(--md-list-item-label-text-color, var(--md-sys-color-on-surface, #1d1b20));font-family:var(--md-list-item-label-text-font, var(--md-sys-typescale-body-large-font, var(--md-ref-typeface-plain, Roboto)));font-size:var(--md-list-item-label-text-size, var(--md-sys-typescale-body-large-size, 1rem));line-height:var(--md-list-item-label-text-line-height, var(--md-sys-typescale-body-large-line-height, 1.5rem));font-weight:var(--md-list-item-label-text-weight, var(--md-sys-typescale-body-large-weight, var(--md-ref-typeface-weight-regular, 400)));min-height:var(--md-list-item-one-line-container-height, 56px);padding-top:var(--md-list-item-top-space, 12px);padding-bottom:var(--md-list-item-bottom-space, 12px);padding-inline-start:var(--md-list-item-leading-space, 16px);padding-inline-end:var(--md-list-item-trailing-space, 16px)}md-item[multiline]{min-height:var(--md-list-item-two-line-container-height, 72px)}[slot=supporting-text]{color:var(--md-list-item-supporting-text-color, var(--md-sys-color-on-surface-variant, #49454f));font-family:var(--md-list-item-supporting-text-font, var(--md-sys-typescale-body-medium-font, var(--md-ref-typeface-plain, Roboto)));font-size:var(--md-list-item-supporting-text-size, var(--md-sys-typescale-body-medium-size, 0.875rem));line-height:var(--md-list-item-supporting-text-line-height, var(--md-sys-typescale-body-medium-line-height, 1.25rem));font-weight:var(--md-list-item-supporting-text-weight, var(--md-sys-typescale-body-medium-weight, var(--md-ref-typeface-weight-regular, 400)))}[slot=trailing-supporting-text]{color:var(--md-list-item-trailing-supporting-text-color, var(--md-sys-color-on-surface-variant, #49454f));font-family:var(--md-list-item-trailing-supporting-text-font, var(--md-sys-typescale-label-small-font, var(--md-ref-typeface-plain, Roboto)));font-size:var(--md-list-item-trailing-supporting-text-size, var(--md-sys-typescale-label-small-size, 0.6875rem));line-height:var(--md-list-item-trailing-supporting-text-line-height, var(--md-sys-typescale-label-small-line-height, 1rem));font-weight:var(--md-list-item-trailing-supporting-text-weight, var(--md-sys-typescale-label-small-weight, var(--md-ref-typeface-weight-medium, 500)))}:is([slot=start],[slot=end])::slotted(*){fill:currentColor}[slot=start]{color:var(--md-list-item-leading-icon-color, var(--md-sys-color-on-surface-variant, #49454f))}[slot=end]{color:var(--md-list-item-trailing-icon-color, var(--md-sys-color-on-surface-variant, #49454f))}@media(forced-colors: active){.disabled slot{color:GrayText}.list-item.disabled{color:GrayText;opacity:1}}
`;/**
 * @license
 * Copyright 2022 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */let $=class extends u{};$.styles=[nt];$=r([L("md-list-item")],$);const T={list:document.getElementById("queueList"),syncBtn:document.getElementById("syncAllBtn"),backBtn:document.getElementById("backBtn")};T.backBtn.addEventListener("click",()=>window.location.href="popup.html");T.syncBtn.addEventListener("click",at);async function z(){const{offlineQueue:i=[]}=await chrome.storage.local.get("offlineQueue"),t=document.getElementById("queueList");if(t.innerHTML="",i.length===0){t.innerHTML='<div class="empty-msg" style="user-select: none;">Warteschlange ist leer</div>';return}i.forEach((e,s)=>{const o=document.createElement("md-list-item");o.headline=e.title||"Kein Titel",o.supportingText=e.url;const n=document.createElement("span");n.slot="headline",n.textContent=e.title||"Kein Titel",o.appendChild(n);const a=document.createElement("span");a.slot="supporting-text",a.textContent=e.url,o.appendChild(a);const g=document.createElement("md-icon-button");g.slot="end",g.innerHTML="<md-icon>delete</md-icon>",g.onclick=I=>{I.stopPropagation(),rt(s)},o.appendChild(g),T.list.appendChild(o)})}async function rt(i){const{offlineQueue:t}=await chrome.storage.local.get("offlineQueue");t.splice(i,1),await chrome.storage.local.set({offlineQueue:t}),z()}async function at(){chrome.runtime.sendMessage({type:"PROCESS_QUEUE"}),setTimeout(z,1e3)}z();
