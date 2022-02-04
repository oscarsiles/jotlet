this.Urls = (function () {
    var data = {"urls": [["admin:app_list", [["admin/%(app_label)s/", ["app_label"]]]], ["admin:auth_group_add", [["admin/auth/group/add/", []]]], ["admin:auth_group_change", [["admin/auth/group/%(object_id)s/change/", ["object_id"]]]], ["admin:auth_group_changelist", [["admin/auth/group/", []]]], ["admin:auth_group_delete", [["admin/auth/group/%(object_id)s/delete/", ["object_id"]]]], ["admin:auth_group_history", [["admin/auth/group/%(object_id)s/history/", ["object_id"]]]], ["admin:auth_user_add", [["admin/auth/user/add/", []]]], ["admin:auth_user_change", [["admin/auth/user/%(object_id)s/change/", ["object_id"]]]], ["admin:auth_user_changelist", [["admin/auth/user/", []]]], ["admin:auth_user_delete", [["admin/auth/user/%(object_id)s/delete/", ["object_id"]]]], ["admin:auth_user_history", [["admin/auth/user/%(object_id)s/history/", ["object_id"]]]], ["admin:auth_user_password_change", [["admin/auth/user/%(id)s/password/", ["id"]]]], ["admin:autocomplete", [["admin/autocomplete/", []]]], ["admin:boards_board_add", [["admin/boards/board/add/", []]]], ["admin:boards_board_change", [["admin/boards/board/%(object_id)s/change/", ["object_id"]]]], ["admin:boards_board_changelist", [["admin/boards/board/", []]]], ["admin:boards_board_delete", [["admin/boards/board/%(object_id)s/delete/", ["object_id"]]]], ["admin:boards_board_history", [["admin/boards/board/%(object_id)s/history/", ["object_id"]]]], ["admin:boards_post_add", [["admin/boards/post/add/", []]]], ["admin:boards_post_change", [["admin/boards/post/%(object_id)s/change/", ["object_id"]]]], ["admin:boards_post_changelist", [["admin/boards/post/", []]]], ["admin:boards_post_delete", [["admin/boards/post/%(object_id)s/delete/", ["object_id"]]]], ["admin:boards_post_history", [["admin/boards/post/%(object_id)s/history/", ["object_id"]]]], ["admin:boards_topic_add", [["admin/boards/topic/add/", []]]], ["admin:boards_topic_change", [["admin/boards/topic/%(object_id)s/change/", ["object_id"]]]], ["admin:boards_topic_changelist", [["admin/boards/topic/", []]]], ["admin:boards_topic_delete", [["admin/boards/topic/%(object_id)s/delete/", ["object_id"]]]], ["admin:boards_topic_history", [["admin/boards/topic/%(object_id)s/history/", ["object_id"]]]], ["admin:index", [["admin/", []]]], ["admin:jsi18n", [["admin/jsi18n/", []]]], ["admin:login", [["admin/login/", []]]], ["admin:logout", [["admin/logout/", []]]], ["admin:password_change", [["admin/password_change/", []]]], ["admin:password_change_done", [["admin/password_change/done/", []]]], ["admin:view_on_site", [["admin/r/%(content_type_id)s/%(object_id)s/", ["content_type_id", "object_id"]]]], ["boards:board", [["boards/%(slug)s/", ["slug"]]]], ["boards:board-create", [["boards/create/", []]]], ["boards:board-delete", [["boards/%(slug)s/delete/", ["slug"]]]], ["boards:board-update", [["boards/%(slug)s/update/", ["slug"]]]], ["boards:index", [["boards/", []]]], ["boards:post-create", [["boards/%(slug)s/topics/%(topic_pk)s/posts/create/", ["slug", "topic_pk"]]]], ["boards:post-delete", [["boards/%(slug)s/topics/%(topic_pk)s/posts/%(pk)s/delete/", ["slug", "topic_pk", "pk"]]]], ["boards:post-update", [["boards/%(slug)s/topics/%(topic_pk)s/posts/%(pk)s/update/", ["slug", "topic_pk", "pk"]]]], ["boards:topic-create", [["boards/%(slug)s/topics/create/", ["slug"]]]], ["boards:topic-delete", [["boards/%(slug)s/topics/%(pk)s/delete/", ["slug", "pk"]]]], ["boards:topic-update", [["boards/%(slug)s/topics/%(pk)s/update/", ["slug", "pk"]]]], ["login", [["accounts/login/", []]]], ["logout", [["accounts/logout/", []]]], ["password_change", [["accounts/password_change/", []]]], ["password_change_done", [["accounts/password_change/done/", []]]], ["password_reset", [["accounts/password_reset/", []]]], ["password_reset_complete", [["accounts/reset/done/", []]]], ["password_reset_confirm", [["accounts/reset/%(uidb64)s/%(token)s/", ["uidb64", "token"]]]], ["password_reset_done", [["accounts/password_reset/done/", []]]]], "prefix": "/"};
    var resolverFactory;
/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	// The require scope
/******/ 	var __webpack_require__ = {};
/******/ 	
/************************************************************************/
/******/ 	/* webpack/runtime/define property getters */
/******/ 	(() => {
/******/ 		// define getter functions for harmony exports
/******/ 		__webpack_require__.d = (exports, definition) => {
/******/ 			for(var key in definition) {
/******/ 				if(__webpack_require__.o(definition, key) && !__webpack_require__.o(exports, key)) {
/******/ 					Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
/******/ 				}
/******/ 			}
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/hasOwnProperty shorthand */
/******/ 	(() => {
/******/ 		__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop))
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/make namespace object */
/******/ 	(() => {
/******/ 		// define __esModule on exports
/******/ 		__webpack_require__.r = (exports) => {
/******/ 			if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 				Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 			}
/******/ 			Object.defineProperty(exports, '__esModule', { value: true });
/******/ 		};
/******/ 	})();
/******/ 	
/************************************************************************/
var __webpack_exports__ = {};
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "UrlResolver": () => (/* binding */ UrlResolver),
/* harmony export */   "factory": () => (/* binding */ factory)
/* harmony export */ });
function _slicedToArray(arr, i) { return _arrayWithHoles(arr) || _iterableToArrayLimit(arr, i) || _unsupportedIterableToArray(arr, i) || _nonIterableRest(); }

function _nonIterableRest() { throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); }

function _unsupportedIterableToArray(o, minLen) { if (!o) return; if (typeof o === "string") return _arrayLikeToArray(o, minLen); var n = Object.prototype.toString.call(o).slice(8, -1); if (n === "Object" && o.constructor) n = o.constructor.name; if (n === "Map" || n === "Set") return Array.from(o); if (n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)) return _arrayLikeToArray(o, minLen); }

function _arrayLikeToArray(arr, len) { if (len == null || len > arr.length) len = arr.length; for (var i = 0, arr2 = new Array(len); i < len; i++) { arr2[i] = arr[i]; } return arr2; }

function _iterableToArrayLimit(arr, i) { var _i = arr == null ? null : typeof Symbol !== "undefined" && arr[Symbol.iterator] || arr["@@iterator"]; if (_i == null) return; var _arr = []; var _n = true; var _d = false; var _s, _e; try { for (_i = _i.call(arr); !(_n = (_s = _i.next()).done); _n = true) { _arr.push(_s.value); if (i && _arr.length === i) break; } } catch (err) { _d = true; _e = err; } finally { try { if (!_n && _i["return"] != null) _i["return"](); } finally { if (_d) throw _e; } } return _arr; }

function _arrayWithHoles(arr) { if (Array.isArray(arr)) return arr; }

function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

var UrlResolver = /*#__PURE__*/function () {
  function UrlResolver(prefix, patterns) {
    _classCallCheck(this, UrlResolver);

    this.prefix = prefix;
    this.patterns = patterns;
    this.reverse = this.reverse.bind(this);
  }

  _createClass(UrlResolver, [{
    key: "reverse",
    value: function reverse() {
      for (var _len = arguments.length, args = new Array(_len), _key = 0; _key < _len; _key++) {
        args[_key] = arguments[_key];
      }

      var validateArgs, buildKwargs;

      if (args.length === 1 && _typeof(args[0]) === 'object') {
        // kwargs mode
        var providedKeys = Object.keys(args[0]);

        validateArgs = function validateArgs(_ref) {
          var _ref2 = _slicedToArray(_ref, 2),
              _urlTemplate = _ref2[0],
              urlParams = _ref2[1];

          // check every needed param was provided (without extra elements)
          return urlParams.length === providedKeys.length && urlParams.every(function (p) {
            return providedKeys.includes(p);
          });
        }; // return first element


        buildKwargs = function buildKwargs() {
          return args[0];
        };
      } else {
        // args mode
        // check every required param
        validateArgs = function validateArgs(_ref3) {
          var _ref4 = _slicedToArray(_ref3, 2),
              _urlTemplate = _ref4[0],
              urlParams = _ref4[1];

          return urlParams.length === args.length;
        }; // build keyword-arguments from arguments


        buildKwargs = function buildKwargs(keys) {
          return keys.reduce(function (kw, key, i) {
            kw[key] = args[i];
            return kw;
          }, {});
        };
      } // search between patterns if one matches provided args


      var urlPattern = this.patterns.find(validateArgs);

      if (!urlPattern) {
        return null;
      }

      var _urlPattern = _slicedToArray(urlPattern, 2),
          urlTemplate = _urlPattern[0],
          urlKwargNames = _urlPattern[1];

      var urlKwargs = buildKwargs(urlKwargNames);
      var url = Object.entries(urlKwargs).reduce(function (partialUrl, _ref5) {
        var _ref6 = _slicedToArray(_ref5, 2),
            pName = _ref6[0],
            pValue = _ref6[1];

        if (pValue === null || pValue === undefined) pValue = ''; // replace variable with param

        return partialUrl.replace("%(".concat(pName, ")s"), pValue);
      }, urlTemplate);
      return "".concat(this.prefix).concat(url);
    }
  }]);

  return UrlResolver;
}();
function factory(config) {
  var urlPatterns = config.urls,
      urlPrefix = config.prefix;
  return urlPatterns.reduce(function (resolver, _ref7) {
    var _ref8 = _slicedToArray(_ref7, 2),
        name = _ref8[0],
        pattern = _ref8[1];

    var urlResolver = new UrlResolver(urlPrefix, pattern);
    resolver[name] = urlResolver.reverse; // turn snake-case into camel-case

    resolver[name.replace(/[-_]+(.)/g, function (_m, p1) {
      return p1.toUpperCase();
    })] = urlResolver.reverse; // turn snake-case into dash-case

    resolver[name.replace(/-/g, '_')] = urlResolver.reverse;
    return resolver;
  }, {});
}
resolverFactory = __webpack_exports__;
/******/ })()
;
    return data ? resolverFactory.factory(data) : resolverFactory.factory;
})();
