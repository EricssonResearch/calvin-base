var ObjectiveJ={};
(function(_1,_2){
if(!Object.create){
Object.create=function(o){
if(arguments.length>1){
throw new Error("Object.create implementation only accepts the first parameter.");
}
function F(){
};
F.prototype=o;
return new F();
};
}
if(!Object.keys){
Object.keys=(function(){
var _3=Object.prototype.hasOwnProperty,_4=!{toString:null}.propertyIsEnumerable("toString"),_5=["toString","toLocaleString","valueOf","hasOwnProperty","isPrototypeOf","propertyIsEnumerable","constructor"],_6=_5.length;
return function(_7){
if(typeof _7!=="object"&&typeof _7!=="function"||_7===null){
throw new TypeError("Object.keys called on non-object");
}
var _8=[];
for(var _9 in _7){
if(_3.call(_7,_9)){
_8.push(_9);
}
}
if(_4){
for(var i=0;i<_6;i++){
if(_3.call(_7,_5[i])){
_8.push(_5[i]);
}
}
}
return _8;
};
})();
}
if(!Array.prototype.indexOf){
Array.prototype.indexOf=function(_a){
"use strict";
if(this===null){
throw new TypeError();
}
var t=new Object(this),_b=t.length>>>0;
if(_b===0){
return -1;
}
var n=0;
if(arguments.length>1){
n=Number(arguments[1]);
if(n!=n){
n=0;
}else{
if(n!==0&&n!=Infinity&&n!=-Infinity){
n=(n>0||-1)*Math.floor(Math.abs(n));
}
}
}
if(n>=_b){
return -1;
}
var k=n>=0?n:Math.max(_b-Math.abs(n),0);
for(;k<_b;k++){
if(k in t&&t[k]===_a){
return k;
}
}
return -1;
};
}
if(!String.prototype.startsWith){
String.prototype.startsWith=function(_c,_d){
_d=_d||0;
return this.substr(_d,_c.length)===_c;
};
}
if(!String.prototype.endsWith){
String.prototype.endsWith=function(_e,_f){
var _10=this.toString();
if(typeof _f!=="number"||!isFinite(_f)||Math.floor(_f)!==_f||_f>_10.length){
_f=_10.length;
}
_f-=_e.length;
var _11=_10.indexOf(_e,_f);
return _11!==-1&&_11===_f;
};
}
if(!this.JSON){
JSON={};
}
(function(){
function f(n){
return n<10?"0"+n:n;
};
if(typeof Date.prototype.toJSON!=="function"){
Date.prototype.toJSON=function(key){
return this.getUTCFullYear()+"-"+f(this.getUTCMonth()+1)+"-"+f(this.getUTCDate())+"T"+f(this.getUTCHours())+":"+f(this.getUTCMinutes())+":"+f(this.getUTCSeconds())+"Z";
};
String.prototype.toJSON=Number.prototype.toJSON=Boolean.prototype.toJSON=function(key){
return this.valueOf();
};
}
var cx=new RegExp("[\\u0000\\u00ad\\u0600-\\u0604\\u070f\\u17b4\\u17b5\\u200c-\\u200f\\u2028-\\u202f\\u2060-\\u206f\\ufeff\\ufff0-\\uffff]","g");
var _12=new RegExp("[\\\\\\\"\\x00-\\x1f\\x7f-\\x9f\\u00ad\\u0600-\\u0604\\u070f\\u17b4\\u17b5\\u200c-\\u200f\\u2028-\\u202f\\u2060-\\u206f\\ufeff\\ufff0-\\uffff]","g");
var gap,_13,_14={"\b":"\\b","\t":"\\t","\n":"\\n","\f":"\\f","\r":"\\r","\"":"\\\"","\\":"\\\\"},rep;
function _15(_16){
_12.lastIndex=0;
return _12.test(_16)?"\""+_16.replace(_12,function(a){
var c=_14[a];
return typeof c==="string"?c:"\\u"+("0000"+(a.charCodeAt(0)).toString(16)).slice(-4);
})+"\"":"\""+_16+"\"";
};
function str(key,_17){
var i,k,v,_18,_19=gap,_1a,_1b=_17[key];
if(_1b&&typeof _1b==="object"&&typeof _1b.toJSON==="function"){
_1b=_1b.toJSON(key);
}
if(typeof rep==="function"){
_1b=rep.call(_17,key,_1b);
}
switch(typeof _1b){
case "string":
return _15(_1b);
case "number":
return isFinite(_1b)?String(_1b):"null";
case "boolean":
case "null":
return String(_1b);
case "object":
if(!_1b){
return "null";
}
gap+=_13;
_1a=[];
if(Object.prototype.toString.apply(_1b)==="[object Array]"){
_18=_1b.length;
for(i=0;i<_18;i+=1){
_1a[i]=str(i,_1b)||"null";
}
v=_1a.length===0?"[]":gap?"[\n"+gap+_1a.join(",\n"+gap)+"\n"+_19+"]":"["+_1a.join(",")+"]";
gap=_19;
return v;
}
if(rep&&typeof rep==="object"){
_18=rep.length;
for(i=0;i<_18;i+=1){
k=rep[i];
if(typeof k==="string"){
v=str(k,_1b);
if(v){
_1a.push(_15(k)+(gap?": ":":")+v);
}
}
}
}else{
for(k in _1b){
if(Object.hasOwnProperty.call(_1b,k)){
v=str(k,_1b);
if(v){
_1a.push(_15(k)+(gap?": ":":")+v);
}
}
}
}
v=_1a.length===0?"{}":gap?"{\n"+gap+_1a.join(",\n"+gap)+"\n"+_19+"}":"{"+_1a.join(",")+"}";
gap=_19;
return v;
}
};
if(typeof JSON.stringify!=="function"){
JSON.stringify=function(_1c,_1d,_1e){
var i;
gap="";
_13="";
if(typeof _1e==="number"){
for(i=0;i<_1e;i+=1){
_13+=" ";
}
}else{
if(typeof _1e==="string"){
_13=_1e;
}
}
rep=_1d;
if(_1d&&typeof _1d!=="function"&&(typeof _1d!=="object"||typeof _1d.length!=="number")){
throw new Error("JSON.stringify");
}
return str("",{"":_1c});
};
}
if(typeof JSON.parse!=="function"){
JSON.parse=function(_1f,_20){
var j;
function _21(_22,key){
var k,v,_23=_22[key];
if(_23&&typeof _23==="object"){
for(k in _23){
if(Object.hasOwnProperty.call(_23,k)){
v=_21(_23,k);
if(v!==_32){
_23[k]=v;
}else{
delete _23[k];
}
}
}
}
return _20.call(_22,key,_23);
};
cx.lastIndex=0;
if(cx.test(_1f)){
_1f=_1f.replace(cx,function(a){
return "\\u"+("0000"+(a.charCodeAt(0)).toString(16)).slice(-4);
});
}
if(/^[\],:{}\s]*$/.test(((_1f.replace(/\\(?:["\\\/bfnrt]|u[0-9a-fA-F]{4})/g,"@")).replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g,"]")).replace(/(?:^|:|,)(?:\s*\[)+/g,""))){
j=eval("("+_1f+")");
return typeof _20==="function"?_21({"":j},""):j;
}
throw new SyntaxError("JSON.parse");
};
}
})();
var _24=/([^%]+|%(?:\d+\$)?[\+\-\ \#0]*[0-9\*]*(.[0-9\*]+)?[hlL]?[cbBdieEfgGosuxXpn%@])/g,_25=/(%)(?:(\d+)\$)?([\+\-\ \#0]*)([0-9\*]*)((?:.[0-9\*]+)?)([hlL]?)([cbBdieEfgGosuxXpn%@])/;
_2.sprintf=function(_26){
var _26=arguments[0],_27=_26.match(_24),_28=0,_29="",arg=1;
for(var i=0;i<_27.length;i++){
var t=_27[i];
if(_26.substring(_28,_28+t.length)!==t){
return _29;
}
_28+=t.length;
if(t.charAt(0)!=="%"){
_29+=t;
}else{
if(t==="%%"){
_29+="%";
}else{
var _2a=t.match(_25);
if(_2a.length!==8||_2a[0]!==t){
return _29;
}
var _2b=_2a[1],_2c=_2a[2],_2d=_2a[3],_2e=_2a[4],_2f=_2a[5],_30=_2a[6],_31=_2a[7];
if(_2c===_32||_2c===null||_2c===""){
_2c=arg++;
}else{
_2c=Number(_2c);
}
var _33=null;
if(_2e=="*"){
_33=arguments[_2c];
}else{
if(_2e!==""){
_33=Number(_2e);
}
}
var _34=null;
if(_2f===".*"){
_34=arguments[_2c];
}else{
if(_2f!==""){
_34=Number(_2f.substring(1));
}
}
var _35=_2d.indexOf("-")>=0,_36=_2d.indexOf("0")>=0,_37="";
if(/[bBdiufeExXo]/.test(_31)){
var num=Number(arguments[_2c]),_38="";
if(num<0){
_38="-";
}else{
if(_2d.indexOf("+")>=0){
_38="+";
}else{
if(_2d.indexOf(" ")>=0){
_38=" ";
}
}
}
if(_31==="d"||_31==="i"||_31==="u"){
var _39=String(Math.abs(Math.floor(num)));
_37=_3a(_38,"",_39,"",_33,_35,_36);
}
if(_31=="f"){
var _39=String(_34!==null?(Math.abs(num)).toFixed(_34):Math.abs(num)),_3b=_2d.indexOf("#")>=0&&_39.indexOf(".")<0?".":"";
_37=_3a(_38,"",_39,_3b,_33,_35,_36);
}
if(_31==="e"||_31==="E"){
var _39=String((Math.abs(num)).toExponential(_34!==null?_34:21)),_3b=_2d.indexOf("#")>=0&&_39.indexOf(".")<0?".":"";
_37=_3a(_38,"",_39,_3b,_33,_35,_36);
}
if(_31=="x"||_31=="X"){
var _39=String((Math.abs(num)).toString(16));
var _3c=_2d.indexOf("#")>=0&&num!=0?"0x":"";
_37=_3a(_38,_3c,_39,"",_33,_35,_36);
}
if(_31=="b"||_31=="B"){
var _39=String((Math.abs(num)).toString(2));
var _3c=_2d.indexOf("#")>=0&&num!=0?"0b":"";
_37=_3a(_38,_3c,_39,"",_33,_35,_36);
}
if(_31=="o"){
var _39=String((Math.abs(num)).toString(8));
var _3c=_2d.indexOf("#")>=0&&num!=0?"0":"";
_37=_3a(_38,_3c,_39,"",_33,_35,_36);
}
if(/[A-Z]/.test(_31)){
_37=_37.toUpperCase();
}else{
_37=_37.toLowerCase();
}
}else{
var _37="";
if(_31==="%"){
_37="%";
}else{
if(_31==="c"){
_37=(String(arguments[_2c])).charAt(0);
}else{
if(_31==="s"||_31==="@"){
_37=String(arguments[_2c]);
}else{
if(_31==="p"||_31==="n"){
_37="";
}
}
}
}
_37=_3a("","",_37,"",_33,_35,false);
}
_29+=_37;
}
}
}
return _29;
};
function _3a(_3d,_3e,_3f,_40,_41,_42,_43){
var _44=_3d.length+_3e.length+_3f.length+_40.length;
if(_42){
return _3d+_3e+_3f+_40+pad(_41-_44," ");
}else{
if(_43){
return _3d+_3e+pad(_41-_44,"0")+_3f+_40;
}else{
return pad(_41-_44," ")+_3d+_3e+_3f+_40;
}
}
};
function pad(n,ch){
return (Array(MAX(0,n)+1)).join(ch);
};
CPLogDisable=false;
var _45="Cappuccino";
var _46=["fatal","error","warn","info","debug","trace"];
var _47=_46[3];
var _48={};
for(var i=0;i<_46.length;i++){
_48[_46[i]]=i;
}
var _49={};
CPLogRegister=function(_4a,_4b,_4c){
CPLogRegisterRange(_4a,_46[0],_4b||_46[_46.length-1],_4c);
};
CPLogRegisterRange=function(_4d,_4e,_4f,_50){
var min=_48[_4e];
var max=_48[_4f];
if(min!==_32&&max!==_32&&min<=max){
for(var i=min;i<=max;i++){
CPLogRegisterSingle(_4d,_46[i],_50);
}
}
};
CPLogRegisterSingle=function(_51,_52,_53){
if(!_49[_52]){
_49[_52]=[];
}
for(var i=0;i<_49[_52].length;i++){
if(_49[_52][i][0]===_51){
_49[_52][i][1]=_53;
return;
}
}
_49[_52].push([_51,_53]);
};
CPLogUnregister=function(_54){
for(var _55 in _49){
for(var i=0;i<_49[_55].length;i++){
if(_49[_55][i][0]===_54){
_49[_55].splice(i--,1);
}
}
}
};
function _56(_57,_58,_59){
if(_59==_32){
_59=_45;
}
if(_58==_32){
_58=_47;
}
var _5a=typeof _57[0]=="string"&&_57.length>1?_2.sprintf.apply(null,_57):String(_57[0]);
if(_49[_58]){
for(var i=0;i<_49[_58].length;i++){
var _5b=_49[_58][i];
_5b[0](_5a,_58,_59,_5b[1]);
}
}
};
CPLog=function(){
_56(arguments);
};
for(var i=0;i<_46.length;i++){
CPLog[_46[i]]=(function(_5c){
return function(){
_56(arguments,_5c);
};
})(_46[i]);
}
var _5d=function(_5e,_5f,_60){
var now=new Date(),_61;
if(_5f===null){
_5f="";
}else{
_5f=_5f||"info";
_5f="["+CPLogColorize(_5f,_5f)+"]";
}
_60=_60||"";
if(_60&&_5f){
_60+=" ";
}
_61=_60+_5f;
if(_61){
_61+=": ";
}
if(typeof _2.sprintf=="function"){
return _2.sprintf("%4d-%02d-%02d %02d:%02d:%02d.%03d %s%s",now.getFullYear(),now.getMonth()+1,now.getDate(),now.getHours(),now.getMinutes(),now.getSeconds(),now.getMilliseconds(),_61,_5e);
}else{
return now+" "+_61+": "+_5e;
}
};
CPLogConsole=function(_62,_63,_64,_65){
if(typeof console!="undefined"){
var _66=(_65||_5d)(_62,_63,_64),_67={"fatal":"error","error":"error","warn":"warn","info":"info","debug":"debug","trace":"debug"}[_63];
if(_67&&console[_67]){
console[_67](_66);
}else{
if(console.log){
console.log(_66);
}
}
}
};
CPLogColorize=function(_68,_69){
return _68;
};
CPLogAlert=function(_6a,_6b,_6c,_6d){
if(typeof alert!="undefined"&&!CPLogDisable){
var _6e=(_6d||_5d)(_6a,_6b,_6c);
CPLogDisable=!confirm(_6e+"\n\n(Click cancel to stop log alerts)");
}
};
var _6f=null;
CPLogPopup=function(_70,_71,_72,_73){
try{
if(CPLogDisable||window.open==_32){
return;
}
if(!_6f||!_6f.document){
_6f=window.open("","_blank","width=600,height=400,status=no,resizable=yes,scrollbars=yes");
if(!_6f){
CPLogDisable=!confirm(_70+"\n\n(Disable pop-up blocking for CPLog window; Click cancel to stop log alerts)");
return;
}
_74(_6f);
}
var _75=_6f.document.createElement("div");
_75.setAttribute("class",_71||"fatal");
var _76=(_73||_5d)(_70,_73?_71:null,_72);
_75.appendChild(_6f.document.createTextNode(_76));
_6f.log.appendChild(_75);
if(_6f.focusEnabled.checked){
_6f.focus();
}
if(_6f.blockEnabled.checked){
_6f.blockEnabled.checked=_6f.confirm(_76+"\nContinue blocking?");
}
if(_6f.scrollEnabled.checked){
_6f.scrollToBottom();
}
}
catch(e){
}
};
var _77="<style type=\"text/css\" media=\"screen\"> body{font:10px Monaco,Courier,\"Courier New\",monospace,mono;padding-top:15px;} div > .fatal,div > .error,div > .warn,div > .info,div > .debug,div > .trace{display:none;overflow:hidden;white-space:pre;padding:0px 5px 0px 5px;margin-top:2px;-moz-border-radius:5px;-webkit-border-radius:5px;} div[wrap=\"yes\"] > div{white-space:normal;} .fatal{background-color:#ffb2b3;} .error{background-color:#ffe2b2;} .warn{background-color:#fdffb2;} .info{background-color:#e4ffb2;} .debug{background-color:#a0e5a0;} .trace{background-color:#99b9ff;} .enfatal .fatal,.enerror .error,.enwarn .warn,.eninfo .info,.endebug .debug,.entrace .trace{display:block;} div#header{background-color:rgba(240,240,240,0.82);position:fixed;top:0px;left:0px;width:100%;border-bottom:1px solid rgba(0,0,0,0.33);text-align:center;} ul#enablers{display:inline-block;margin:1px 15px 0 15px;padding:2px 0 2px 0;} ul#enablers li{display:inline;padding:0px 5px 0px 5px;margin-left:4px;-moz-border-radius:5px;-webkit-border-radius:5px;} [enabled=\"no\"]{opacity:0.25;} ul#options{display:inline-block;margin:0 15px 0px 15px;padding:0 0px;} ul#options li{margin:0 0 0 0;padding:0 0 0 0;display:inline;} </style>";
function _74(_78){
var doc=_78.document;
doc.writeln("<html><head><title></title>"+_77+"</head><body></body></html>");
doc.title=_45+" Run Log";
var _79=(doc.getElementsByTagName("head"))[0];
var _7a=(doc.getElementsByTagName("body"))[0];
var _7b=window.location.protocol+"//"+window.location.host+window.location.pathname;
_7b=_7b.substring(0,_7b.lastIndexOf("/")+1);
var div=doc.createElement("div");
div.setAttribute("id","header");
_7a.appendChild(div);
var ul=doc.createElement("ul");
ul.setAttribute("id","enablers");
div.appendChild(ul);
for(var i=0;i<_46.length;i++){
var li=doc.createElement("li");
li.setAttribute("id","en"+_46[i]);
li.setAttribute("class",_46[i]);
li.setAttribute("onclick","toggle(this);");
li.setAttribute("enabled","yes");
li.appendChild(doc.createTextNode(_46[i]));
ul.appendChild(li);
}
var ul=doc.createElement("ul");
ul.setAttribute("id","options");
div.appendChild(ul);
var _7c={"focus":["Focus",false],"block":["Block",false],"wrap":["Wrap",false],"scroll":["Scroll",true],"close":["Close",true]};
for(o in _7c){
var li=doc.createElement("li");
ul.appendChild(li);
_78[o+"Enabled"]=doc.createElement("input");
_78[o+"Enabled"].setAttribute("id",o);
_78[o+"Enabled"].setAttribute("type","checkbox");
if(_7c[o][1]){
_78[o+"Enabled"].setAttribute("checked","checked");
}
li.appendChild(_78[o+"Enabled"]);
var _7d=doc.createElement("label");
_7d.setAttribute("for",o);
_7d.appendChild(doc.createTextNode(_7c[o][0]));
li.appendChild(_7d);
}
_78.log=doc.createElement("div");
_78.log.setAttribute("class","enerror endebug enwarn eninfo enfatal entrace");
_7a.appendChild(_78.log);
_78.toggle=function(_7e){
var _7f=_7e.getAttribute("enabled")=="yes"?"no":"yes";
_7e.setAttribute("enabled",_7f);
if(_7f=="yes"){
_78.log.className+=" "+_7e.id;
}else{
_78.log.className=_78.log.className.replace(new RegExp("[\\s]*"+_7e.id,"g"),"");
}
};
_78.scrollToBottom=function(){
_78.scrollTo(0,_7a.offsetHeight);
};
_78.wrapEnabled.addEventListener("click",function(){
_78.log.setAttribute("wrap",_78.wrapEnabled.checked?"yes":"no");
},false);
_78.addEventListener("keydown",function(e){
var e=e||_78.event;
if(e.keyCode==75&&(e.ctrlKey||e.metaKey)){
while(_78.log.firstChild){
_78.log.removeChild(_78.log.firstChild);
}
e.preventDefault();
}
},"false");
window.addEventListener("unload",function(){
if(_78&&_78.closeEnabled&&_78.closeEnabled.checked){
CPLogDisable=true;
_78.close();
}
},false);
_78.addEventListener("unload",function(){
if(!CPLogDisable){
CPLogDisable=!confirm("Click cancel to stop logging");
}
},false);
};
CPLogDefault=typeof window==="object"&&window.console?CPLogConsole:CPLogPopup;
var _32;
if(typeof window!=="undefined"){
window.setNativeTimeout=window.setTimeout;
window.clearNativeTimeout=window.clearTimeout;
window.setNativeInterval=window.setInterval;
window.clearNativeInterval=window.clearInterval;
}
NO=false;
YES=true;
nil=null;
Nil=null;
NULL=null;
ABS=Math.abs;
ASIN=Math.asin;
ACOS=Math.acos;
ATAN=Math.atan;
ATAN2=Math.atan2;
SIN=Math.sin;
COS=Math.cos;
TAN=Math.tan;
EXP=Math.exp;
POW=Math.pow;
CEIL=Math.ceil;
FLOOR=Math.floor;
ROUND=Math.round;
MIN=Math.min;
MAX=Math.max;
RAND=Math.random;
SQRT=Math.sqrt;
E=Math.E;
LN2=Math.LN2;
LN10=Math.LN10;
LOG=Math.log;
LOG2E=Math.LOG2E;
LOG10E=Math.LOG10E;
PI=Math.PI;
PI2=Math.PI*2;
PI_2=Math.PI/2;
SQRT1_2=Math.SQRT1_2;
SQRT2=Math.SQRT2;
function _80(_81){
this._eventListenersForEventNames={};
this._owner=_81;
};
_80.prototype.addEventListener=function(_82,_83){
var _84=this._eventListenersForEventNames;
if(!_85.call(_84,_82)){
var _86=[];
_84[_82]=_86;
}else{
var _86=_84[_82];
}
var _87=_86.length;
while(_87--){
if(_86[_87]===_83){
return;
}
}
_86.push(_83);
};
_80.prototype.removeEventListener=function(_88,_89){
var _8a=this._eventListenersForEventNames;
if(!_85.call(_8a,_88)){
return;
}
var _8b=_8a[_88],_8c=_8b.length;
while(_8c--){
if(_8b[_8c]===_89){
return _8b.splice(_8c,1);
}
}
};
_80.prototype.dispatchEvent=function(_8d){
var _8e=_8d.type,_8f=this._eventListenersForEventNames;
if(_85.call(_8f,_8e)){
var _90=this._eventListenersForEventNames[_8e],_91=0,_92=_90.length;
for(;_91<_92;++_91){
_90[_91](_8d);
}
}
var _93=(this._owner||this)["on"+_8e];
if(_93){
_93(_8d);
}
};
var _94=0,_95=null,_96=[];
function _97(_98){
var _99=_94;
if(_95===null){
window.setNativeTimeout(function(){
var _9a=_96,_9b=0,_9c=_96.length;
++_94;
_95=null;
_96=[];
for(;_9b<_9c;++_9b){
_9a[_9b]();
}
},0);
}
return function(){
var _9d=arguments;
if(_94>_99){
_98.apply(this,_9d);
}else{
_96.push(function(){
_98.apply(this,_9d);
});
}
};
};
var _9e=null;
if(window.XMLHttpRequest){
_9e=window.XMLHttpRequest;
}else{
if(window.ActiveXObject!==_32){
var _9f=["Msxml2.XMLHTTP.3.0","Msxml2.XMLHTTP.6.0"],_a0=_9f.length;
while(_a0--){
try{
var _a1=_9f[_a0];
new ActiveXObject(_a1);
_9e=function(){
return new ActiveXObject(_a1);
};
break;
}
catch(anException){
}
}
}
}
CFHTTPRequest=function(){
this._isOpen=false;
this._requestHeaders={};
this._mimeType=null;
this._eventDispatcher=new _80(this);
this._nativeRequest=new _9e();
this._withCredentials=false;
this._timeout=60000;
var _a2=this;
this._stateChangeHandler=function(){
_bb(_a2);
};
this._timeoutHandler=function(){
_b9(_a2);
};
this._nativeRequest.onreadystatechange=this._stateChangeHandler;
this._nativeRequest.ontimeout=this._timeoutHandler;
if(CFHTTPRequest.AuthenticationDelegate!==nil){
this._eventDispatcher.addEventListener("HTTP403",function(){
CFHTTPRequest.AuthenticationDelegate(_a2);
});
}
};
CFHTTPRequest.UninitializedState=0;
CFHTTPRequest.LoadingState=1;
CFHTTPRequest.LoadedState=2;
CFHTTPRequest.InteractiveState=3;
CFHTTPRequest.CompleteState=4;
CFHTTPRequest.AuthenticationDelegate=nil;
CFHTTPRequest.prototype.status=function(){
try{
return this._nativeRequest.status||0;
}
catch(anException){
return 0;
}
};
CFHTTPRequest.prototype.statusText=function(){
try{
return this._nativeRequest.statusText||"";
}
catch(anException){
return "";
}
};
CFHTTPRequest.prototype.readyState=function(){
return this._nativeRequest.readyState;
};
CFHTTPRequest.prototype.success=function(){
var _a3=this.status();
if(_a3>=200&&_a3<300){
return YES;
}
return _a3===0&&this.responseText()&&(this.responseText()).length;
};
CFHTTPRequest.prototype.responseXML=function(){
var _a4=this._nativeRequest.responseXML;
if(_a4&&_9e===window.XMLHttpRequest&&_a4.documentRoot){
return _a4;
}
return _a5(this.responseText());
};
CFHTTPRequest.prototype.responsePropertyList=function(){
var _a6=this.responseText();
if(CFPropertyList.sniffedFormatOfString(_a6)===CFPropertyList.FormatXML_v1_0){
return CFPropertyList.propertyListFromXML(this.responseXML());
}
return CFPropertyList.propertyListFromString(_a6);
};
CFHTTPRequest.prototype.responseText=function(){
return this._nativeRequest.responseText;
};
CFHTTPRequest.prototype.setRequestHeader=function(_a7,_a8){
this._requestHeaders[_a7]=_a8;
};
CFHTTPRequest.prototype.getResponseHeader=function(_a9){
return this._nativeRequest.getResponseHeader(_a9);
};
CFHTTPRequest.prototype.setTimeout=function(_aa){
this._timeout=_aa;
if(this._isOpen){
this._nativeRequest.timeout=_aa;
}
};
CFHTTPRequest.prototype.getTimeout=function(_ab){
return this._timeout;
};
CFHTTPRequest.prototype.getAllResponseHeaders=function(){
return this._nativeRequest.getAllResponseHeaders();
};
CFHTTPRequest.prototype.overrideMimeType=function(_ac){
this._mimeType=_ac;
};
CFHTTPRequest.prototype.open=function(_ad,_ae,_af,_b0,_b1){
var _b2;
this._isOpen=true;
this._URL=_ae;
this._async=_af;
this._method=_ad;
this._user=_b0;
this._password=_b1;
requestReturnValue=this._nativeRequest.open(_ad,_ae,_af,_b0,_b1);
if(this._async){
this._nativeRequest.withCredentials=this._withCredentials;
this._nativeRequest.timeout=this._timeout;
}
return requestReturnValue;
};
CFHTTPRequest.prototype.send=function(_b3){
if(!this._isOpen){
delete this._nativeRequest.onreadystatechange;
delete this._nativeRequest.ontimeout;
this._nativeRequest.open(this._method,this._URL,this._async,this._user,this._password);
this._nativeRequest.ontimeout=this._timeoutHandler;
this._nativeRequest.onreadystatechange=this._stateChangeHandler;
}
for(var i in this._requestHeaders){
if(this._requestHeaders.hasOwnProperty(i)){
this._nativeRequest.setRequestHeader(i,this._requestHeaders[i]);
}
}
if(this._mimeType&&"overrideMimeType" in this._nativeRequest){
this._nativeRequest.overrideMimeType(this._mimeType);
}
this._isOpen=false;
try{
return this._nativeRequest.send(_b3);
}
catch(anException){
this._eventDispatcher.dispatchEvent({type:"failure",request:this});
}
};
CFHTTPRequest.prototype.abort=function(){
this._isOpen=false;
return this._nativeRequest.abort();
};
CFHTTPRequest.prototype.addEventListener=function(_b4,_b5){
this._eventDispatcher.addEventListener(_b4,_b5);
};
CFHTTPRequest.prototype.removeEventListener=function(_b6,_b7){
this._eventDispatcher.removeEventListener(_b6,_b7);
};
CFHTTPRequest.prototype.setWithCredentials=function(_b8){
this._withCredentials=_b8;
if(this._isOpen&&this._async){
this._nativeRequest.withCredentials=_b8;
}
};
CFHTTPRequest.prototype.withCredentials=function(){
return this._withCredentials;
};
CFHTTPRequest.prototype.isTimeoutRequest=function(){
return !this.success()&&!this._nativeRequest.response&&!this._nativeRequest.responseText&&!this._nativeRequest.responseType&&!this._nativeRequest.responseURL&&!this._nativeRequest.responseXML;
};
function _b9(_ba){
_ba._eventDispatcher.dispatchEvent({type:"timeout",request:_ba});
};
function _bb(_bc){
var _bd=_bc._eventDispatcher,_be=["uninitialized","loading","loaded","interactive","complete"];
_bd.dispatchEvent({type:"readystatechange",request:_bc});
if(_be[_bc.readyState()]==="complete"){
var _bf="HTTP"+_bc.status();
_bd.dispatchEvent({type:_bf,request:_bc});
var _c0=_bc.success()?"success":"failure";
_bd.dispatchEvent({type:_c0,request:_bc});
_bd.dispatchEvent({type:_be[_bc.readyState()],request:_bc});
}else{
_bd.dispatchEvent({type:_be[_bc.readyState()],request:_bc});
}
};
function _c1(_c2,_c3,_c4,_c5){
var _c6=new CFHTTPRequest();
if(_c2.pathExtension()==="plist"){
_c6.overrideMimeType("text/xml");
}
var _c7=0,_c8=null;
function _c9(_ca){
_c5(_ca.loaded-_c7);
_c7=_ca.loaded;
};
function _cb(_cc){
if(_c5&&_c8===null){
_c5((_cc.request.responseText()).length);
}
_c3(_cc);
};
if(_2.asyncLoader){
_c6.onsuccess=_97(_cb);
_c6.onfailure=_97(_c4);
}else{
_c6.onsuccess=_cb;
_c6.onfailure=_c4;
}
if(_c5){
var _cd=true;
if(document.all){
_cd=!!window.atob;
}
if(_cd){
try{
_c8=_2.asyncLoader?_97(_c9):_c9;
_c6._nativeRequest.onprogress=_c8;
}
catch(anException){
_c8=null;
}
}
}
_c6.open("GET",_c2.absoluteString(),_2.asyncLoader);
_c6.send("");
};
_2.asyncLoader=YES;
_2.Asynchronous=_97;
_2.determineAndDispatchHTTPRequestEvents=_bb;
var _ce=0;
objj_generateObjectUID=function(){
return _ce++;
};
CFPropertyList=function(){
this._UID=objj_generateObjectUID();
};
CFPropertyList.DTDRE=/^\s*(?:<\?\s*xml\s+version\s*=\s*\"1.0\"[^>]*\?>\s*)?(?:<\!DOCTYPE[^>]*>\s*)?/i;
CFPropertyList.XMLRE=/^\s*(?:<\?\s*xml\s+version\s*=\s*\"1.0\"[^>]*\?>\s*)?(?:<\!DOCTYPE[^>]*>\s*)?<\s*plist[^>]*\>/i;
CFPropertyList.FormatXMLDTD="<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">";
CFPropertyList.Format280NorthMagicNumber="280NPLIST";
(CFPropertyList.FormatOpenStep=1,CFPropertyList.FormatXML_v1_0=100,CFPropertyList.FormatBinary_v1_0=200,CFPropertyList.Format280North_v1_0=-1000);
CFPropertyList.sniffedFormatOfString=function(_cf){
if(_cf.match(CFPropertyList.XMLRE)){
return CFPropertyList.FormatXML_v1_0;
}
if(_cf.substr(0,CFPropertyList.Format280NorthMagicNumber.length)===CFPropertyList.Format280NorthMagicNumber){
return CFPropertyList.Format280North_v1_0;
}
return NULL;
};
CFPropertyList.dataFromPropertyList=function(_d0,_d1){
var _d2=new CFMutableData();
_d2.setRawString(CFPropertyList.stringFromPropertyList(_d0,_d1));
return _d2;
};
CFPropertyList.stringFromPropertyList=function(_d3,_d4){
if(!_d4){
_d4=CFPropertyList.Format280North_v1_0;
}
var _d5=_d6[_d4];
return _d5["start"]()+_d7(_d3,_d5)+_d5["finish"]();
};
function _d7(_d8,_d9){
var _da=typeof _d8,_db=_d8.valueOf(),_dc=typeof _db;
if(_da!==_dc){
_da=_dc;
_d8=_db;
}
if(_d8===YES||_d8===NO){
_da="boolean";
}else{
if(_da==="number"){
if(FLOOR(_d8)===_d8&&(""+_d8).indexOf("e")==-1){
_da="integer";
}else{
_da="real";
}
}else{
if(_da!=="string"){
if(_d8.slice){
_da="array";
}else{
_da="dictionary";
}
}
}
}
return _d9[_da](_d8,_d9);
};
var _d6={};
_d6[CFPropertyList.FormatXML_v1_0]={"start":function(){
return CFPropertyList.FormatXMLDTD+"<plist version = \"1.0\">";
},"finish":function(){
return "</plist>";
},"string":function(_dd){
return "<string>"+_de(_dd)+"</string>";
},"boolean":function(_df){
return _df?"<true/>":"<false/>";
},"integer":function(_e0){
return "<integer>"+_e0+"</integer>";
},"real":function(_e1){
return "<real>"+_e1+"</real>";
},"array":function(_e2,_e3){
var _e4=0,_e5=_e2.length,_e6="<array>";
for(;_e4<_e5;++_e4){
_e6+=_d7(_e2[_e4],_e3);
}
return _e6+"</array>";
},"dictionary":function(_e7,_e8){
var _e9=_e7._keys,_a0=0,_ea=_e9.length,_eb="<dict>";
for(;_a0<_ea;++_a0){
var key=_e9[_a0];
_eb+="<key>"+key+"</key>";
_eb+=_d7(_e7.valueForKey(key),_e8);
}
return _eb+"</dict>";
}};
var _ec="A",_ed="D",_ee="f",_ef="d",_f0="S",_f1="T",_f2="F",_f3="K",_f4="E";
_d6[CFPropertyList.Format280North_v1_0]={"start":function(){
return CFPropertyList.Format280NorthMagicNumber+";1.0;";
},"finish":function(){
return "";
},"string":function(_f5){
return _f0+";"+_f5.length+";"+_f5;
},"boolean":function(_f6){
return (_f6?_f1:_f2)+";";
},"integer":function(_f7){
var _f8=""+_f7;
return _ef+";"+_f8.length+";"+_f8;
},"real":function(_f9){
var _fa=""+_f9;
return _ee+";"+_fa.length+";"+_fa;
},"array":function(_fb,_fc){
var _fd=0,_fe=_fb.length,_ff=_ec+";";
for(;_fd<_fe;++_fd){
_ff+=_d7(_fb[_fd],_fc);
}
return _ff+_f4+";";
},"dictionary":function(_100,_101){
var keys=_100._keys,_a0=0,_102=keys.length,_103=_ed+";";
for(;_a0<_102;++_a0){
var key=keys[_a0];
_103+=_f3+";"+key.length+";"+key;
_103+=_d7(_100.valueForKey(key),_101);
}
return _103+_f4+";";
}};
var _104="xml",_105="#document",_106="plist",_107="key",_108="dict",_109="array",_10a="string",_10b="date",_10c="true",_10d="false",_10e="real",_10f="integer",_110="data";
var _111=function(_112){
var text="",_a0=0,_113=_112.length;
for(;_a0<_113;++_a0){
var node=_112[_a0];
if(node.nodeType===3||node.nodeType===4){
text+=node.nodeValue;
}else{
if(node.nodeType!==8){
text+=_111(node.childNodes);
}
}
}
return text;
};
var _114=function(_115,_116,_117){
var node=_115;
node=node.firstChild;
if(node!==NULL&&(node.nodeType===8||node.nodeType===3)){
while((node=node.nextSibling)&&(node.nodeType===8||node.nodeType===3)){
}
}
if(node){
return node;
}
if(String(_115.nodeName)===_109||String(_115.nodeName)===_108){
_117.pop();
}else{
if(node===_116){
return NULL;
}
node=_115;
while((node=node.nextSibling)&&(node.nodeType===8||node.nodeType===3)){
}
if(node){
return node;
}
}
node=_115;
while(node){
var next=node;
while((next=next.nextSibling)&&(next.nodeType===8||next.nodeType===3)){
}
if(next){
return next;
}
var node=node.parentNode;
if(_116&&node===_116){
return NULL;
}
_117.pop();
}
return NULL;
};
CFPropertyList.propertyListFromData=function(_118,_119){
return CFPropertyList.propertyListFromString(_118.rawString(),_119);
};
CFPropertyList.propertyListFromString=function(_11a,_11b){
if(!_11b){
_11b=CFPropertyList.sniffedFormatOfString(_11a);
}
if(_11b===CFPropertyList.FormatXML_v1_0){
return CFPropertyList.propertyListFromXML(_11a);
}
if(_11b===CFPropertyList.Format280North_v1_0){
return _11c(_11a);
}
return NULL;
};
var _ec="A",_ed="D",_ee="f",_ef="d",_f0="S",_f1="T",_f2="F",_f3="K",_f4="E";
function _11c(_11d){
var _11e=new _11f(_11d),_120=NULL,key="",_121=NULL,_122=NULL,_123=[],_124=NULL;
while(_120=_11e.getMarker()){
if(_120===_f4){
_123.pop();
continue;
}
var _125=_123.length;
if(_125){
_124=_123[_125-1];
}
if(_120===_f3){
key=_11e.getString();
_120=_11e.getMarker();
}
switch(_120){
case _ec:
_121=[];
_123.push(_121);
break;
case _ed:
_121=new CFMutableDictionary();
_123.push(_121);
break;
case _ee:
_121=parseFloat(_11e.getString());
break;
case _ef:
_121=parseInt(_11e.getString(),10);
break;
case _f0:
_121=_11e.getString();
break;
case _f1:
_121=YES;
break;
case _f2:
_121=NO;
break;
default:
throw new Error("*** "+_120+" marker not recognized in Plist.");
}
if(!_122){
_122=_121;
}else{
if(_124){
if(_124.slice){
_124.push(_121);
}else{
_124.setValueForKey(key,_121);
}
}
}
}
return _122;
};
function _de(_126){
return ((((_126.replace(/&/g,"&amp;")).replace(/"/g,"&quot;")).replace(/'/g,"&apos;")).replace(/</g,"&lt;")).replace(/>/g,"&gt;");
};
function _127(_128){
return ((((_128.replace(/&quot;/g,"\"")).replace(/&apos;/g,"'")).replace(/&lt;/g,"<")).replace(/&gt;/g,">")).replace(/&amp;/g,"&");
};
function _a5(_129){
if(window.DOMParser){
return ((new window.DOMParser()).parseFromString(_129,"text/xml")).documentElement;
}else{
if(window.ActiveXObject){
XMLNode=new ActiveXObject("Microsoft.XMLDOM");
var _12a=_129.match(CFPropertyList.DTDRE);
if(_12a){
_129=_129.substr(_12a[0].length);
}
XMLNode.loadXML(_129);
return XMLNode;
}
}
return NULL;
};
CFPropertyList.propertyListFromXML=function(_12b){
var _12c=_12b;
if(_12b.valueOf&&typeof _12b.valueOf()==="string"){
_12c=_a5(_12b);
}
while(String(_12c.nodeName)===_105||String(_12c.nodeName)===_104){
_12c=_12c.firstChild;
if(_12c!==NULL&&(_12c.nodeType===8||_12c.nodeType===3)){
while((_12c=_12c.nextSibling)&&(_12c.nodeType===8||_12c.nodeType===3)){
}
}
}
if(_12c.nodeType===10){
while((_12c=_12c.nextSibling)&&(_12c.nodeType===8||_12c.nodeType===3)){
}
}
if(!(String(_12c.nodeName)===_106)){
return NULL;
}
var key="",_12d=NULL,_12e=NULL,_12f=_12c,_130=[],_131=NULL;
while(_12c=_114(_12c,_12f,_130)){
var _132=_130.length;
if(_132){
_131=_130[_132-1];
}
if(String(_12c.nodeName)===_107){
key=_12c.textContent||_12c.textContent!==""&&_111([_12c]);
while((_12c=_12c.nextSibling)&&(_12c.nodeType===8||_12c.nodeType===3)){
}
}
switch(String(String(_12c.nodeName))){
case _109:
_12d=[];
_130.push(_12d);
break;
case _108:
_12d=new CFMutableDictionary();
_130.push(_12d);
break;
case _10e:
_12d=parseFloat(_12c.textContent||_12c.textContent!==""&&_111([_12c]));
break;
case _10f:
_12d=parseInt(_12c.textContent||_12c.textContent!==""&&_111([_12c]),10);
break;
case _10a:
if(_12c.getAttribute("type")==="base64"){
_12d=_12c.firstChild?CFData.decodeBase64ToString(_12c.textContent||_12c.textContent!==""&&_111([_12c])):"";
}else{
_12d=_127(_12c.firstChild?_12c.textContent||_12c.textContent!==""&&_111([_12c]):"");
}
break;
case _10b:
var _133=Date.parseISO8601(_12c.textContent||_12c.textContent!==""&&_111([_12c]));
_12d=isNaN(_133)?new Date():new Date(_133);
break;
case _10c:
_12d=YES;
break;
case _10d:
_12d=NO;
break;
case _110:
_12d=new CFMutableData();
var _134=_12c.firstChild?CFData.decodeBase64ToArray(_12c.textContent||_12c.textContent!==""&&_111([_12c]),YES):[];
_12d.setBytes(_134);
break;
default:
throw new Error("*** "+String(_12c.nodeName)+" tag not recognized in Plist.");
}
if(!_12e){
_12e=_12d;
}else{
if(_131){
if(_131.slice){
_131.push(_12d);
}else{
_131.setValueForKey(key,_12d);
}
}
}
}
return _12e;
};
kCFPropertyListOpenStepFormat=CFPropertyList.FormatOpenStep;
kCFPropertyListXMLFormat_v1_0=CFPropertyList.FormatXML_v1_0;
kCFPropertyListBinaryFormat_v1_0=CFPropertyList.FormatBinary_v1_0;
kCFPropertyList280NorthFormat_v1_0=CFPropertyList.Format280North_v1_0;
CFPropertyListCreate=function(){
return new CFPropertyList();
};
CFPropertyListCreateFromXMLData=function(data){
return CFPropertyList.propertyListFromData(data,CFPropertyList.FormatXML_v1_0);
};
CFPropertyListCreateXMLData=function(_135){
return CFPropertyList.dataFromPropertyList(_135,CFPropertyList.FormatXML_v1_0);
};
CFPropertyListCreateFrom280NorthData=function(data){
return CFPropertyList.propertyListFromData(data,CFPropertyList.Format280North_v1_0);
};
CFPropertyListCreate280NorthData=function(_136){
return CFPropertyList.dataFromPropertyList(_136,CFPropertyList.Format280North_v1_0);
};
CPPropertyListCreateFromData=function(data,_137){
return CFPropertyList.propertyListFromData(data,_137);
};
CPPropertyListCreateData=function(_138,_139){
return CFPropertyList.dataFromPropertyList(_138,_139);
};
CFDictionary=function(_13a){
this._keys=[];
this._count=0;
this._buckets={};
this._UID=objj_generateObjectUID();
};
var _13b=Array.prototype.indexOf,_85=Object.prototype.hasOwnProperty;
CFDictionary.prototype.copy=function(){
return this;
};
CFDictionary.prototype.mutableCopy=function(){
var _13c=new CFMutableDictionary(),keys=this._keys,_13d=this._count;
_13c._keys=keys.slice();
_13c._count=_13d;
var _13e=0,_13f=this._buckets,_140=_13c._buckets;
for(;_13e<_13d;++_13e){
var key=keys[_13e];
_140[key]=_13f[key];
}
return _13c;
};
CFDictionary.prototype.containsKey=function(aKey){
return _85.apply(this._buckets,[aKey]);
};
CFDictionary.prototype.containsValue=function(_141){
var keys=this._keys,_142=this._buckets,_a0=0,_143=keys.length;
for(;_a0<_143;++_a0){
if(_142[keys[_a0]]===_141){
return YES;
}
}
return NO;
};
CFDictionary.prototype.count=function(){
return this._count;
};
CFDictionary.prototype.countOfKey=function(aKey){
return this.containsKey(aKey)?1:0;
};
CFDictionary.prototype.countOfValue=function(_144){
var keys=this._keys,_145=this._buckets,_a0=0,_146=keys.length,_147=0;
for(;_a0<_146;++_a0){
if(_145[keys[_a0]]===_144){
++_147;
}
}
return _147;
};
CFDictionary.prototype.keys=function(){
return this._keys.slice();
};
CFDictionary.prototype.valueForKey=function(aKey){
var _148=this._buckets;
if(!_85.apply(_148,[aKey])){
return nil;
}
return _148[aKey];
};
CFDictionary.prototype.toString=function(){
var _149="{\n",keys=this._keys,_a0=0,_14a=this._count;
for(;_a0<_14a;++_a0){
var key=keys[_a0];
_149+="\t"+key+" = \""+((String(this.valueForKey(key))).split("\n")).join("\n\t")+"\"\n";
}
return _149+"}";
};
CFMutableDictionary=function(_14b){
CFDictionary.apply(this,[]);
};
CFMutableDictionary.prototype=new CFDictionary();
CFMutableDictionary.prototype.copy=function(){
return this.mutableCopy();
};
CFMutableDictionary.prototype.addValueForKey=function(aKey,_14c){
if(this.containsKey(aKey)){
return;
}
++this._count;
this._keys.push(aKey);
this._buckets[aKey]=_14c;
};
CFMutableDictionary.prototype.removeValueForKey=function(aKey){
var _14d=-1;
if(_13b){
_14d=_13b.call(this._keys,aKey);
}else{
var keys=this._keys,_a0=0,_14e=keys.length;
for(;_a0<_14e;++_a0){
if(keys[_a0]===aKey){
_14d=_a0;
break;
}
}
}
if(_14d===-1){
return;
}
--this._count;
this._keys.splice(_14d,1);
delete this._buckets[aKey];
};
CFMutableDictionary.prototype.removeAllValues=function(){
this._count=0;
this._keys=[];
this._buckets={};
};
CFMutableDictionary.prototype.replaceValueForKey=function(aKey,_14f){
if(!this.containsKey(aKey)){
return;
}
this._buckets[aKey]=_14f;
};
CFMutableDictionary.prototype.setValueForKey=function(aKey,_150){
if(_150===nil||_150===_32){
this.removeValueForKey(aKey);
}else{
if(this.containsKey(aKey)){
this.replaceValueForKey(aKey,_150);
}else{
this.addValueForKey(aKey,_150);
}
}
};
kCFErrorLocalizedDescriptionKey="CPLocalizedDescription";
kCFErrorLocalizedFailureReasonKey="CPLocalizedFailureReason";
kCFErrorLocalizedRecoverySuggestionKey="CPLocalizedRecoverySuggestion";
kCFErrorDescriptionKey="CPDescription";
kCFErrorUnderlyingErrorKey="CPUnderlyingError";
kCFErrorURLKey="CPURL";
kCFErrorFilePathKey="CPFilePath";
kCFErrorDomainCappuccino="CPCappuccinoErrorDomain";
kCFErrorDomainCocoa=kCFErrorDomainCappuccino;
CFError=function(_151,code,_152){
this._domain=_151||NULL;
this._code=code||0;
this._userInfo=_152||new CFDictionary();
this._UID=objj_generateObjectUID();
};
CFError.prototype.domain=function(){
return this._domain;
};
CFError.prototype.code=function(){
return this._code;
};
CFError.prototype.description=function(){
var _153=this._userInfo.valueForKey(kCFErrorLocalizedDescriptionKey);
if(_153){
return _153;
}
var _154=this._userInfo.valueForKey(kCFErrorLocalizedFailureReasonKey);
if(_154){
var _155="The operation couldn’t be completed. "+_154;
return _155;
}
var _156="",desc=this._userInfo.valueForKey(kCFErrorDescriptionKey);
if(desc){
var _156="The operation couldn’t be completed. (error "+this._code+" - "+desc+")";
}else{
var _156="The operation couldn’t be completed. (error "+this._code+")";
}
return _156;
};
CFError.prototype.failureReason=function(){
return this._userInfo.valueForKey(kCFErrorLocalizedFailureReasonKey);
};
CFError.prototype.recoverySuggestion=function(){
return this._userInfo.valueForKey(kCFErrorLocalizedRecoverySuggestionKey);
};
CFError.prototype.userInfo=function(){
return this._userInfo;
};
CFErrorCreate=function(_157,code,_158){
return new CFError(_157,code,_158);
};
CFErrorCreateWithUserInfoKeysAndValues=function(_159,code,_15a,_15b,_15c){
var _15d=new CFMutableDictionary();
while(_15c--){
_15d.setValueForKey(_15a[_15c],_15b[_15c]);
}
return new CFError(_159,code,_15d);
};
CFErrorGetCode=function(err){
return err.code();
};
CFErrorGetDomain=function(err){
return err.domain();
};
CFErrorCopyDescription=function(err){
return err.description();
};
CFErrorCopyUserInfo=function(err){
return err.userInfo();
};
CFErrorCopyFailureReason=function(err){
return err.failureReason();
};
CFErrorCopyRecoverySuggestion=function(err){
return err.recoverySuggestion();
};
kCFURLErrorUnknown=-998;
kCFURLErrorCancelled=-999;
kCFURLErrorBadURL=-1000;
kCFURLErrorTimedOut=-1001;
kCFURLErrorUnsupportedURL=-1002;
kCFURLErrorCannotFindHost=-1003;
kCFURLErrorCannotConnectToHost=-1004;
kCFURLErrorNetworkConnectionLost=-1005;
kCFURLErrorDNSLookupFailed=-1006;
kCFURLErrorHTTPTooManyRedirects=-1007;
kCFURLErrorResourceUnavailable=-1008;
kCFURLErrorNotConnectedToInternet=-1009;
kCFURLErrorRedirectToNonExistentLocation=-1010;
kCFURLErrorBadServerResponse=-1011;
kCFURLErrorUserCancelledAuthentication=-1012;
kCFURLErrorUserAuthenticationRequired=-1013;
kCFURLErrorZeroByteResource=-1014;
kCFURLErrorCannotDecodeRawData=-1015;
kCFURLErrorCannotDecodeContentData=-1016;
kCFURLErrorCannotParseResponse=-1017;
kCFURLErrorRequestBodyStreamExhausted=-1021;
kCFURLErrorFileDoesNotExist=-1100;
kCFURLErrorFileIsDirectory=-1101;
kCFURLErrorNoPermissionsToReadFile=-1102;
kCFURLErrorDataLengthExceedsMaximum=-1103;
CFData=function(){
this._rawString=NULL;
this._propertyList=NULL;
this._propertyListFormat=NULL;
this._JSONObject=NULL;
this._bytes=NULL;
this._base64=NULL;
};
CFData.prototype.propertyList=function(){
if(!this._propertyList){
this._propertyList=CFPropertyList.propertyListFromString(this.rawString());
}
return this._propertyList;
};
CFData.prototype.JSONObject=function(){
if(!this._JSONObject){
try{
this._JSONObject=JSON.parse(this.rawString());
}
catch(anException){
}
}
return this._JSONObject;
};
CFData.prototype.rawString=function(){
if(this._rawString===NULL){
if(this._propertyList){
this._rawString=CFPropertyList.stringFromPropertyList(this._propertyList,this._propertyListFormat);
}else{
if(this._JSONObject){
this._rawString=JSON.stringify(this._JSONObject);
}else{
if(this._bytes){
this._rawString=CFData.bytesToString(this._bytes);
}else{
if(this._base64){
this._rawString=CFData.decodeBase64ToString(this._base64,true);
}else{
throw new Error("Can't convert data to string.");
}
}
}
}
}
return this._rawString;
};
CFData.prototype.bytes=function(){
if(this._bytes===NULL){
var _15e=CFData.stringToBytes(this.rawString());
this.setBytes(_15e);
}
return this._bytes;
};
CFData.prototype.base64=function(){
if(this._base64===NULL){
var _15f;
if(this._bytes){
_15f=CFData.encodeBase64Array(this._bytes);
}else{
_15f=CFData.encodeBase64String(this.rawString());
}
this.setBase64String(_15f);
}
return this._base64;
};
CFMutableData=function(){
CFData.call(this);
};
CFMutableData.prototype=new CFData();
function _160(_161){
this._rawString=NULL;
this._propertyList=NULL;
this._propertyListFormat=NULL;
this._JSONObject=NULL;
this._bytes=NULL;
this._base64=NULL;
};
CFMutableData.prototype.setPropertyList=function(_162,_163){
_160(this);
this._propertyList=_162;
this._propertyListFormat=_163;
};
CFMutableData.prototype.setJSONObject=function(_164){
_160(this);
this._JSONObject=_164;
};
CFMutableData.prototype.setRawString=function(_165){
_160(this);
this._rawString=_165;
};
CFMutableData.prototype.setBytes=function(_166){
_160(this);
this._bytes=_166;
};
CFMutableData.prototype.setBase64String=function(_167){
_160(this);
this._base64=_167;
};
var _168=["A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z","a","b","c","d","e","f","g","h","i","j","k","l","m","n","o","p","q","r","s","t","u","v","w","x","y","z","0","1","2","3","4","5","6","7","8","9","+","/","="],_169=[];
for(var i=0;i<_168.length;i++){
_169[_168[i].charCodeAt(0)]=i;
}
CFData.decodeBase64ToArray=function(_16a,_16b){
if(_16b){
_16a=_16a.replace(/[^A-Za-z0-9\+\/\=]/g,"");
}
var pad=(_16a[_16a.length-1]=="="?1:0)+(_16a[_16a.length-2]=="="?1:0),_16c=_16a.length,_16d=[];
var i=0;
while(i<_16c){
var bits=_169[_16a.charCodeAt(i++)]<<18|_169[_16a.charCodeAt(i++)]<<12|_169[_16a.charCodeAt(i++)]<<6|_169[_16a.charCodeAt(i++)];
_16d.push((bits&16711680)>>16);
_16d.push((bits&65280)>>8);
_16d.push(bits&255);
}
if(pad>0){
return _16d.slice(0,-1*pad);
}
return _16d;
};
CFData.encodeBase64Array=function(_16e){
var pad=(3-_16e.length%3)%3,_16f=_16e.length+pad,_170=[];
if(pad>0){
_16e.push(0);
}
if(pad>1){
_16e.push(0);
}
var i=0;
while(i<_16f){
var bits=_16e[i++]<<16|_16e[i++]<<8|_16e[i++];
_170.push(_168[(bits&16515072)>>18]);
_170.push(_168[(bits&258048)>>12]);
_170.push(_168[(bits&4032)>>6]);
_170.push(_168[bits&63]);
}
if(pad>0){
_170[_170.length-1]="=";
_16e.pop();
}
if(pad>1){
_170[_170.length-2]="=";
_16e.pop();
}
return _170.join("");
};
CFData.decodeBase64ToString=function(_171,_172){
return CFData.bytesToString(CFData.decodeBase64ToArray(_171,_172));
};
CFData.decodeBase64ToUtf16String=function(_173,_174){
return CFData.bytesToUtf16String(CFData.decodeBase64ToArray(_173,_174));
};
CFData.bytesToString=function(_175){
return String.fromCharCode.apply(NULL,_175);
};
CFData.stringToBytes=function(_176){
var temp=[];
for(var i=0;i<_176.length;i++){
temp.push(_176.charCodeAt(i));
}
return temp;
};
CFData.encodeBase64String=function(_177){
var temp=[];
for(var i=0;i<_177.length;i++){
temp.push(_177.charCodeAt(i));
}
return CFData.encodeBase64Array(temp);
};
CFData.bytesToUtf16String=function(_178){
var temp=[];
for(var i=0;i<_178.length;i+=2){
temp.push(_178[i+1]<<8|_178[i]);
}
return String.fromCharCode.apply(NULL,temp);
};
CFData.encodeBase64Utf16String=function(_179){
var temp=[];
for(var i=0;i<_179.length;i++){
var c=_179.charCodeAt(i);
temp.push(c&255);
temp.push((c&65280)>>8);
}
return CFData.encodeBase64Array(temp);
};
var _17a,_17b,_17c=0;
function _17d(){
if(++_17c!==1){
return;
}
_17a={};
_17b={};
};
function _17e(){
_17c=MAX(_17c-1,0);
if(_17c!==0){
return;
}
delete _17a;
delete _17b;
};
var _17f=new RegExp("^"+"(?:"+"([^:/?#]+):"+")?"+"(?:"+"(//)"+"("+"(?:"+"("+"([^:@]*)"+":?"+"([^:@]*)"+")?"+"@"+")?"+"([^:/?#]*)"+"(?::(\\d*))?"+")"+")?"+"([^?#]*)"+"(?:\\?([^#]*))?"+"(?:#(.*))?");
var _180=["url","scheme","authorityRoot","authority","userInfo","user","password","domain","portNumber","path","queryString","fragment"];
function _181(aURL){
if(aURL._parts){
return aURL._parts;
}
var _182=aURL.string(),_183=_182.match(/^mhtml:/);
if(_183){
_182=_182.substr("mhtml:".length);
}
if(_17c>0&&_85.call(_17b,_182)){
aURL._parts=_17b[_182];
return aURL._parts;
}
aURL._parts={};
var _184=aURL._parts,_185=_17f.exec(_182),_a0=_185.length;
while(_a0--){
_184[_180[_a0]]=_185[_a0]||NULL;
}
_184.portNumber=parseInt(_184.portNumber,10);
if(isNaN(_184.portNumber)){
_184.portNumber=-1;
}
_184.pathComponents=[];
if(_184.path){
var _186=_184.path.split("/"),_187=_184.pathComponents,_188=_186.length;
for(_a0=0;_a0<_188;++_a0){
var _189=_186[_a0];
if(_189){
_187.push(_189);
}else{
if(_a0===0){
_187.push("/");
}
}
}
_184.pathComponents=_187;
}
if(_183){
_184.url="mhtml:"+_184.url;
_184.scheme="mhtml:"+_184.scheme;
}
if(_17c>0){
_17b[_182]=_184;
}
return _184;
};
CFURL=function(aURL,_18a){
aURL=aURL||"";
if(aURL instanceof CFURL){
if(!_18a){
return new CFURL(aURL.absoluteString());
}
var _18b=aURL.baseURL();
if(_18b){
_18a=new CFURL(_18b.absoluteURL(),_18a);
}
aURL=aURL.string();
}
if(_17c>0){
var _18c=aURL+" "+(_18a&&_18a.UID()||"");
if(_85.call(_17a,_18c)){
return _17a[_18c];
}
_17a[_18c]=this;
}
if(aURL.match(/^data:/)){
var _18d={},_a0=_180.length;
while(_a0--){
_18d[_180[_a0]]="";
}
_18d.url=aURL;
_18d.scheme="data";
_18d.pathComponents=[];
this._parts=_18d;
this._standardizedURL=this;
this._absoluteURL=this;
}
this._UID=objj_generateObjectUID();
this._string=aURL;
this._baseURL=_18a;
};
CFURL.prototype.UID=function(){
return this._UID;
};
var _18e={};
CFURL.prototype.mappedURL=function(){
return _18e[this.absoluteString()]||this;
};
CFURL.setMappedURLForURL=function(_18f,_190){
_18e[_18f.absoluteString()]=_190;
};
CFURL.prototype.schemeAndAuthority=function(){
var _191="",_192=this.scheme();
if(_192){
_191+=_192+":";
}
var _193=this.authority();
if(_193){
_191+="//"+_193;
}
return _191;
};
CFURL.prototype.absoluteString=function(){
if(this._absoluteString===_32){
this._absoluteString=(this.absoluteURL()).string();
}
return this._absoluteString;
};
CFURL.prototype.toString=function(){
return this.absoluteString();
};
function _194(aURL){
aURL=aURL.standardizedURL();
var _195=aURL.baseURL();
if(!_195){
return aURL;
}
var _196=aURL._parts||_181(aURL),_197,_198=_195.absoluteURL(),_199=_198._parts||_181(_198);
if(!_196.scheme&&_196.authorityRoot){
_197=_19a(_196);
_197.scheme=_195.scheme();
}else{
if(_196.scheme||_196.authority){
_197=_196;
}else{
_197={};
_197.scheme=_199.scheme;
_197.authority=_199.authority;
_197.userInfo=_199.userInfo;
_197.user=_199.user;
_197.password=_199.password;
_197.domain=_199.domain;
_197.portNumber=_199.portNumber;
_197.queryString=_196.queryString;
_197.fragment=_196.fragment;
var _19b=_196.pathComponents;
if(_19b.length&&_19b[0]==="/"){
_197.path=_196.path;
_197.pathComponents=_19b;
}else{
var _19c=_199.pathComponents,_19d=_19c.concat(_19b);
if(!_195.hasDirectoryPath()&&_19c.length){
_19d.splice(_19c.length-1,1);
}
if(_19b.length&&(_19b[0]===".."||_19b[0]===".")){
_19e(_19d,YES);
}
_197.pathComponents=_19d;
_197.path=_19f(_19d,_19b.length<=0||aURL.hasDirectoryPath());
}
}
}
var _1a0=_1a1(_197),_1a2=new CFURL(_1a0);
_1a2._parts=_197;
_1a2._standardizedURL=_1a2;
_1a2._standardizedString=_1a0;
_1a2._absoluteURL=_1a2;
_1a2._absoluteString=_1a0;
return _1a2;
};
function _19f(_1a3,_1a4){
var path=_1a3.join("/");
if(path.length&&path.charAt(0)==="/"){
path=path.substr(1);
}
if(_1a4){
path+="/";
}
return path;
};
function _19e(_1a5,_1a6){
var _1a7=0,_1a8=0,_1a9=_1a5.length,_1aa=_1a6?_1a5:[],_1ab=NO;
for(;_1a7<_1a9;++_1a7){
var _1ac=_1a5[_1a7];
if(_1ac===""){
continue;
}
if(_1ac==="."){
_1ab=_1a8===0;
continue;
}
if(_1ac!==".."||_1a8===0||_1aa[_1a8-1]===".."){
_1aa[_1a8]=_1ac;
_1a8++;
continue;
}
if(_1a8>0&&_1aa[_1a8-1]!=="/"){
--_1a8;
}
}
if(_1ab&&_1a8===0){
_1aa[_1a8++]=".";
}
_1aa.length=_1a8;
return _1aa;
};
function _1a1(_1ad){
var _1ae="",_1af=_1ad.scheme;
if(_1af){
_1ae+=_1af+":";
}
var _1b0=_1ad.authority;
if(_1b0){
_1ae+="//"+_1b0;
}
_1ae+=_1ad.path;
var _1b1=_1ad.queryString;
if(_1b1){
_1ae+="?"+_1b1;
}
var _1b2=_1ad.fragment;
if(_1b2){
_1ae+="#"+_1b2;
}
return _1ae;
};
CFURL.prototype.absoluteURL=function(){
if(this._absoluteURL===_32){
this._absoluteURL=_194(this);
}
return this._absoluteURL;
};
CFURL.prototype.standardizedURL=function(){
if(this._standardizedURL===_32){
var _1b3=this._parts||_181(this),_1b4=_1b3.pathComponents,_1b5=_19e(_1b4,NO);
var _1b6=_19f(_1b5,this.hasDirectoryPath());
if(_1b3.path===_1b6){
this._standardizedURL=this;
}else{
var _1b7=_19a(_1b3);
_1b7.pathComponents=_1b5;
_1b7.path=_1b6;
var _1b8=new CFURL(_1a1(_1b7),this.baseURL());
_1b8._parts=_1b7;
_1b8._standardizedURL=_1b8;
this._standardizedURL=_1b8;
}
}
return this._standardizedURL;
};
function _19a(_1b9){
var _1ba={},_1bb=_180.length;
while(_1bb--){
var _1bc=_180[_1bb];
_1ba[_1bc]=_1b9[_1bc];
}
return _1ba;
};
CFURL.prototype.string=function(){
return this._string;
};
CFURL.prototype.authority=function(){
var _1bd=(this._parts||_181(this)).authority;
if(_1bd){
return _1bd;
}
var _1be=this.baseURL();
return _1be&&_1be.authority()||"";
};
CFURL.prototype.hasDirectoryPath=function(){
var _1bf=this._hasDirectoryPath;
if(_1bf===_32){
var path=this.path();
if(!path){
return NO;
}
if(path.charAt(path.length-1)==="/"){
return YES;
}
var _1c0=this.lastPathComponent();
_1bf=_1c0==="."||_1c0==="..";
this._hasDirectoryPath=_1bf;
}
return _1bf;
};
CFURL.prototype.hostName=function(){
return this.authority();
};
CFURL.prototype.fragment=function(){
return (this._parts||_181(this)).fragment;
};
CFURL.prototype.lastPathComponent=function(){
if(this._lastPathComponent===_32){
var _1c1=this.pathComponents(),_1c2=_1c1.length;
if(!_1c2){
this._lastPathComponent="";
}else{
this._lastPathComponent=_1c1[_1c2-1];
}
}
return this._lastPathComponent;
};
CFURL.prototype.path=function(){
return (this._parts||_181(this)).path;
};
CFURL.prototype.createCopyDeletingLastPathComponent=function(){
var _1c3=this._parts||_181(this),_1c4=_19e(_1c3.pathComponents,NO);
if(_1c4.length>0){
if(_1c4.length>1||_1c4[0]!=="/"){
_1c4.pop();
}
}
var _1c5=_1c4.length===1&&_1c4[0]==="/";
_1c3.pathComponents=_1c4;
_1c3.path=_1c5?"/":_19f(_1c4,NO);
return new CFURL(_1a1(_1c3));
};
CFURL.prototype.pathComponents=function(){
return (this._parts||_181(this)).pathComponents;
};
CFURL.prototype.pathExtension=function(){
var _1c6=this.lastPathComponent();
if(!_1c6){
return NULL;
}
_1c6=_1c6.replace(/^\.*/,"");
var _1c7=_1c6.lastIndexOf(".");
return _1c7<=0?"":_1c6.substring(_1c7+1);
};
CFURL.prototype.queryString=function(){
return (this._parts||_181(this)).queryString;
};
CFURL.prototype.scheme=function(){
var _1c8=this._scheme;
if(_1c8===_32){
_1c8=(this._parts||_181(this)).scheme;
if(!_1c8){
var _1c9=this.baseURL();
_1c8=_1c9&&_1c9.scheme();
}
this._scheme=_1c8;
}
return _1c8;
};
CFURL.prototype.user=function(){
return (this._parts||_181(this)).user;
};
CFURL.prototype.password=function(){
return (this._parts||_181(this)).password;
};
CFURL.prototype.portNumber=function(){
return (this._parts||_181(this)).portNumber;
};
CFURL.prototype.domain=function(){
return (this._parts||_181(this)).domain;
};
CFURL.prototype.baseURL=function(){
return this._baseURL;
};
CFURL.prototype.asDirectoryPathURL=function(){
if(this.hasDirectoryPath()){
return this;
}
var _1ca=this.lastPathComponent();
if(_1ca!=="/"){
_1ca="./"+_1ca;
}
return new CFURL(_1ca+"/",this);
};
function _1cb(aURL){
if(!aURL._resourcePropertiesForKeys){
aURL._resourcePropertiesForKeys=new CFMutableDictionary();
}
return aURL._resourcePropertiesForKeys;
};
CFURL.prototype.resourcePropertyForKey=function(aKey){
return (_1cb(this)).valueForKey(aKey);
};
CFURL.prototype.setResourcePropertyForKey=function(aKey,_1cc){
(_1cb(this)).setValueForKey(aKey,_1cc);
};
CFURL.prototype.staticResourceData=function(){
var data=new CFMutableData();
data.setRawString((_1cd.resourceAtURL(this)).contents());
return data;
};
function _11f(_1ce){
this._string=_1ce;
var _1cf=_1ce.indexOf(";");
this._magicNumber=_1ce.substr(0,_1cf);
this._location=_1ce.indexOf(";",++_1cf);
this._version=_1ce.substring(_1cf,this._location++);
};
_11f.prototype.magicNumber=function(){
return this._magicNumber;
};
_11f.prototype.version=function(){
return this._version;
};
_11f.prototype.getMarker=function(){
var _1d0=this._string,_1d1=this._location;
if(_1d1>=_1d0.length){
return null;
}
var next=_1d0.indexOf(";",_1d1);
if(next<0){
return null;
}
var _1d2=_1d0.substring(_1d1,next);
if(_1d2==="e"){
return null;
}
this._location=next+1;
return _1d2;
};
_11f.prototype.getString=function(){
var _1d3=this._string,_1d4=this._location;
if(_1d4>=_1d3.length){
return null;
}
var next=_1d3.indexOf(";",_1d4);
if(next<0){
return null;
}
var size=parseInt(_1d3.substring(_1d4,next),10),text=_1d3.substr(next+1,size);
this._location=next+1+size;
return text;
};
var _1d5=0,_1d6=1<<0,_1d7=1<<1,_1d8=1<<2,_1d9=1<<3,_1da=1<<4,_1db=1<<5;
var _1dc={},_1dd={},_1de={},_1df=(new Date()).getTime(),_1e0=0,_1e1=0;
var _1e2="CPBundleDefaultBrowserLanguage",_1e3="CPBundleDefaultLanguage";
CFBundle=function(aURL){
aURL=(_1e4(aURL)).asDirectoryPathURL();
var _1e5=aURL.absoluteString(),_1e6=_1dc[_1e5];
if(_1e6){
return _1e6;
}
_1dc[_1e5]=this;
this._bundleURL=aURL;
this._resourcesDirectoryURL=new CFURL("Resources/",aURL);
this._staticResource=NULL;
this._isValid=NO;
this._loadStatus=_1d5;
this._loadRequests=[];
this._infoDictionary=new CFDictionary();
this._eventDispatcher=new _80(this);
this._localizableStrings=[];
this._loadedLanguage=NULL;
};
CFBundle.environments=function(){
return ["Browser","ObjJ"];
};
CFBundle.bundleContainingURL=function(aURL){
aURL=new CFURL(".",_1e4(aURL));
var _1e7,_1e8=aURL.absoluteString();
while(!_1e7||_1e7!==_1e8){
var _1e9=_1dc[_1e8];
if(_1e9&&_1e9._isValid){
return _1e9;
}
aURL=new CFURL("..",aURL);
_1e7=_1e8;
_1e8=aURL.absoluteString();
}
return NULL;
};
CFBundle.mainBundle=function(){
return new CFBundle(_1ea);
};
function _1eb(_1ec,_1ed){
if(_1ed){
_1dd[_1ec.name]=_1ed;
}
};
function _1ee(){
_1dc={};
_1dd={};
_1de={};
_1e0=0;
_1e1=0;
};
CFBundle.bundleForClass=function(_1ef){
return _1dd[_1ef.name]||CFBundle.mainBundle();
};
CFBundle.bundleWithIdentifier=function(_1f0){
return _1de[_1f0]||NULL;
};
CFBundle.prototype.bundleURL=function(){
return this._bundleURL.absoluteURL();
};
CFBundle.prototype.resourcesDirectoryURL=function(){
return this._resourcesDirectoryURL;
};
CFBundle.prototype.resourceURL=function(_1f1,_1f2,_1f3,_1f4){
if(_1f2){
_1f1=_1f1+"."+_1f2;
}
if(_1f4){
_1f1=_1f4+_1f1;
}
if(_1f3){
_1f1=_1f3+"/"+_1f1;
}
var _1f5=(new CFURL(_1f1,this.resourcesDirectoryURL())).mappedURL();
return _1f5.absoluteURL();
};
CFBundle.prototype.mostEligibleEnvironmentURL=function(){
if(this._mostEligibleEnvironmentURL===_32){
this._mostEligibleEnvironmentURL=new CFURL(this.mostEligibleEnvironment()+".environment/",this.bundleURL());
}
return this._mostEligibleEnvironmentURL;
};
CFBundle.prototype.executableURL=function(){
if(this._executableURL===_32){
var _1f6=this.valueForInfoDictionaryKey("CPBundleExecutable");
if(!_1f6){
this._executableURL=NULL;
}else{
this._executableURL=new CFURL(_1f6,this.mostEligibleEnvironmentURL());
}
}
return this._executableURL;
};
CFBundle.prototype.infoDictionary=function(){
return this._infoDictionary;
};
CFBundle.prototype.loadedLanguage=function(){
return this._loadedLanguage;
};
CFBundle.prototype.valueForInfoDictionaryKey=function(aKey){
return this._infoDictionary.valueForKey(aKey);
};
CFBundle.prototype.identifier=function(){
return this._infoDictionary.valueForKey("CPBundleIdentifier");
};
CFBundle.prototype.hasSpritedImages=function(){
var _1f7=this._infoDictionary.valueForKey("CPBundleEnvironmentsWithImageSprites")||[],_a0=_1f7.length,_1f8=this.mostEligibleEnvironment();
while(_a0--){
if(_1f7[_a0]===_1f8){
return YES;
}
}
return NO;
};
CFBundle.prototype.environments=function(){
return this._infoDictionary.valueForKey("CPBundleEnvironments")||["ObjJ"];
};
CFBundle.prototype.mostEligibleEnvironment=function(_1f9){
_1f9=_1f9||this.environments();
var _1fa=CFBundle.environments(),_a0=0,_1fb=_1fa.length,_1fc=_1f9.length;
for(;_a0<_1fb;++_a0){
var _1fd=0,_1fe=_1fa[_a0];
for(;_1fd<_1fc;++_1fd){
if(_1fe===_1f9[_1fd]){
return _1fe;
}
}
}
return NULL;
};
CFBundle.prototype.isLoading=function(){
return this._loadStatus&_1d6;
};
CFBundle.prototype.isLoaded=function(){
return !!(this._loadStatus&_1db);
};
CFBundle.prototype.load=function(_1ff){
if(this._loadStatus!==_1d5){
return;
}
this._loadStatus=_1d6|_1d7;
var self=this,_200=this.bundleURL(),_201=new CFURL("..",_200);
if(_201.absoluteString()===_200.absoluteString()){
_201=_201.schemeAndAuthority();
}
_1cd.resolveResourceAtURL(_201,YES,function(_202){
var _203=_200.lastPathComponent();
self._staticResource=_202._children[_203]||new _1cd(_200,_202,YES,NO);
function _204(_205){
self._loadStatus&=~_1d7;
var _206=_205.request.responsePropertyList();
self._isValid=!!_206||CFBundle.mainBundle()===self;
if(_206){
self._infoDictionary=_206;
var _207=self._infoDictionary.valueForKey("CPBundleIdentifier");
if(_207){
_1de[_207]=self;
}
}
if(!self._infoDictionary){
_209(self,new Error("Could not load bundle at \""+path+"\""));
return;
}
if(self===CFBundle.mainBundle()&&self.valueForInfoDictionaryKey("CPApplicationSize")){
_1e1=(self.valueForInfoDictionaryKey("CPApplicationSize")).valueForKey("executable")||0;
}
_24a(self);
_20d(self,_1ff);
};
function _208(){
self._isValid=CFBundle.mainBundle()===self;
self._loadStatus=_1d5;
_209(self,new Error("Could not load bundle at \""+self.bundleURL()+"\""));
};
new _c1(new CFURL("Info.plist",self.bundleURL()),_204,_208);
});
};
function _209(_20a,_20b){
_20c(_20a._staticResource);
_20a._eventDispatcher.dispatchEvent({type:"error",error:_20b,bundle:_20a});
};
function _20d(_20e,_20f){
if(!_20e.mostEligibleEnvironment()){
return _210();
}
_211(_20e,_212,_210,_213);
_214(_20e,_212,_210,_213);
_215(_20e,_212,_210,_213);
if(_20e._loadStatus===_1d6){
return _212();
}
function _210(_216){
var _217=_20e._loadRequests,_218=_217.length;
while(_218--){
_217[_218].abort();
}
this._loadRequests=[];
_20e._loadStatus=_1d5;
_209(_20e,_216||new Error("Could not recognize executable code format in Bundle "+_20e));
};
function _213(_219){
if((typeof CPApp==="undefined"||!CPApp||!CPApp._finishedLaunching)&&typeof OBJJ_PROGRESS_CALLBACK==="function"){
_1e0+=_219;
var _21a=_1e1?MAX(MIN(1,_1e0/_1e1),0):0;
OBJJ_PROGRESS_CALLBACK(_21a,_1e1,_20e.bundlePath());
}
};
function _212(){
if(_20e._loadStatus===_1d6){
_20e._loadStatus=_1db;
}else{
return;
}
_20c(_20e._staticResource);
function _21b(){
_20e._eventDispatcher.dispatchEvent({type:"load",bundle:_20e});
};
if(_20f){
_21c(_20e,_21b);
}else{
_21b();
}
};
};
function _211(_21d,_21e,_21f,_220){
var _221=_21d.executableURL();
if(!_221){
return;
}
_21d._loadStatus|=_1d8;
new _c1(_221,function(_222){
try{
_223(_21d,_222.request.responseText(),_221);
_21d._loadStatus&=~_1d8;
_21e();
}
catch(anException){
_21f(anException);
}
},_21f,_220);
};
function _224(_225){
return "mhtml:"+new CFURL("MHTMLTest.txt",_225.mostEligibleEnvironmentURL());
};
function _226(_227){
if(_228===_229){
return new CFURL("dataURLs.txt",_227.mostEligibleEnvironmentURL());
}
if(_228===_22a||_228===_22b){
return new CFURL("MHTMLPaths.txt",_227.mostEligibleEnvironmentURL());
}
return NULL;
};
function _214(_22c,_22d,_22e,_22f){
if(!_22c.hasSpritedImages()){
return;
}
_22c._loadStatus|=_1d9;
if(!_230()){
return _231(_224(_22c),function(){
_214(_22c,_22d,_22e,_22f);
});
}
var _232=_226(_22c);
if(!_232){
_22c._loadStatus&=~_1d9;
return _22d();
}
new _c1(_232,function(_233){
try{
_223(_22c,_233.request.responseText(),_232);
_22c._loadStatus&=~_1d9;
_22d();
}
catch(anException){
_22e(anException);
}
},_22e,_22f);
};
function _215(_234,_235,_236,_237){
var _238=_234._loadedLanguage;
if(!_238){
return;
}
var _239=_234.valueForInfoDictionaryKey("CPBundleLocalizableStrings");
if(!_239){
return;
}
var self=_234,_23a=_239.length,_23b=new CFURL(_238+".lproj/",self.resourcesDirectoryURL()),_23c=0;
for(var i=0;i<_23a;i++){
var _23d=_239[i];
function _23e(_23f){
var _240=_23f.request.responseText(),_241=(new CFURL(_23f.request._URL)).lastPathComponent();
try{
_242(self,_240,_241);
if(++_23c==_23a){
_234._loadStatus&=~_1da;
_235();
}
}
catch(e){
_236(new Error("Error when parsing the localizable file "+_241));
}
};
_234._loadStatus|=_1da;
new _c1(new CFURL(_23d,_23b),_23e,_236,_237);
}
};
function _242(_243,_244,_245){
var _246={},_247=_244.split("\n"),_248;
_243._localizableStrings[_245]=_246;
for(var i=0;i<_247.length;i++){
var line=_247[i];
if(line[0]=="/"){
_248=(line.substring(2,line.length-2)).trim();
continue;
}
if(line[0]=="\""){
var _249=line.split("\"");
var key=_249[1];
if(!(key in _246)){
_246[key]=_249[3];
}
key+=_248;
if(!(key in _246)){
_246[key]=_249[3];
}
continue;
}
}
};
function _24a(_24b){
if(_24b._loadedLanguage){
return;
}
var _24c=_24b.valueForInfoDictionaryKey(_1e3);
if(_24c!=_1e2&&_24c){
_24b._loadedLanguage=_24c;
return;
}
if(typeof navigator=="undefined"){
return;
}
var _24d=typeof navigator.language!=="undefined"?navigator.language:navigator.userLanguage;
if(!_24d){
return;
}
_24b._loadedLanguage=_24d.substring(0,2);
};
var _24e=[],_228=-1,_24f=0,_229=1,_22a=2,_22b=3;
function _230(){
return _228!==-1;
};
function _231(_250,_251){
if(_230()){
return;
}
_24e.push(_251);
if(_24e.length>1){
return;
}
_24e.push(function(){
var size=0,_252=(CFBundle.mainBundle()).valueForInfoDictionaryKey("CPApplicationSize");
if(!_252){
return;
}
switch(_228){
case _229:
size=_252.valueForKey("data");
break;
case _22a:
case _22b:
size=_252.valueForKey("mhtml");
break;
}
_1e1+=size;
});
_253([_229,"data:image/gif;base64,R0lGODlhAQABAIAAAMc9BQAAACH5BAAAAAAALAAAAAABAAEAAAICRAEAOw==",_22a,_250+"!test",_22b,_250+"?"+_1df+"!test"]);
};
function _254(){
var _255=_24e.length;
while(_255--){
_24e[_255]();
}
};
function _253(_256){
if(!("Image" in _1)||_256.length<2){
_228=_24f;
_254();
return;
}
var _257=new Image();
_257.onload=function(){
if(_257.width===1&&_257.height===1){
_228=_256[0];
_254();
}else{
_257.onerror();
}
};
_257.onerror=function(){
_253(_256.slice(2));
};
_257.src=_256[1];
};
function _21c(_258,_259){
var _25a=[_258._staticResource];
function _25b(_25c){
for(;_25c<_25a.length;++_25c){
var _25d=_25a[_25c];
if(_25d.isNotFound()){
continue;
}
if(_25d.isFile()){
var _25e=new _808(_25d.URL());
if(_25e.hasLoadedFileDependencies()){
_25e.execute();
}else{
_25e.loadFileDependencies(function(){
_25b(_25c);
});
return;
}
}else{
if((_25d.URL()).absoluteString()===(_258.resourcesDirectoryURL()).absoluteString()){
continue;
}
var _25f=_25d.children();
for(var name in _25f){
if(_85.call(_25f,name)){
_25a.push(_25f[name]);
}
}
}
}
_259();
};
_25b(0);
};
var _260="@STATIC",_261="p",_262="u",_263="c",_264="t",_265="I",_266="i";
function _223(_267,_268,_269){
var _26a=new _11f(_268);
if(_26a.magicNumber()!==_260){
throw new Error("Could not read static file: "+_269);
}
if(_26a.version()!=="1.0"){
throw new Error("Could not read static file: "+_269);
}
var _26b,_26c=_267.bundleURL(),file=NULL;
while(_26b=_26a.getMarker()){
var text=_26a.getString();
if(_26b===_261){
var _26d=new CFURL(text,_26c),_26e=_1cd.resourceAtURL(new CFURL(".",_26d),YES);
file=new _1cd(_26d,_26e,NO,YES);
}else{
if(_26b===_262){
var URL=new CFURL(text,_26c),_26f=_26a.getString();
if(_26f.indexOf("mhtml:")===0){
_26f="mhtml:"+new CFURL(_26f.substr("mhtml:".length),_26c);
if(_228===_22b){
var _270=_26f.indexOf("!"),_271=_26f.substring(0,_270),_272=_26f.substring(_270);
_26f=_271+"?"+_1df+_272;
}
}
CFURL.setMappedURLForURL(URL,new CFURL(_26f));
var _26e=_1cd.resourceAtURL(new CFURL(".",URL),YES);
new _1cd(URL,_26e,NO,YES);
}else{
if(_26b===_264){
file.write(text);
}
}
}
}
};
CFBundle.prototype.addEventListener=function(_273,_274){
this._eventDispatcher.addEventListener(_273,_274);
};
CFBundle.prototype.removeEventListener=function(_275,_276){
this._eventDispatcher.removeEventListener(_275,_276);
};
CFBundle.prototype.onerror=function(_277){
throw _277.error;
};
CFBundle.prototype.bundlePath=function(){
return (this.bundleURL()).path();
};
CFBundle.prototype.path=function(){
CPLog.warn("CFBundle.prototype.path is deprecated, use CFBundle.prototype.bundlePath instead.");
return this.bundlePath.apply(this,arguments);
};
CFBundle.prototype.pathForResource=function(_278,_279,_27a,_27b){
return (this.resourceURL(_278,_279,_27a,_27b)).absoluteString();
};
CFBundleCopyLocalizedString=function(_27c,key,_27d,_27e){
return CFCopyLocalizedStringWithDefaultValue(key,_27e,_27c,_27d,"");
};
CFBundleCopyBundleLocalizations=function(_27f){
return [this._loadedLanguage];
};
CFCopyLocalizedString=function(key,_280){
return CFCopyLocalizedStringFromTable(key,"Localizable",_280);
};
CFCopyLocalizedStringFromTable=function(key,_281,_282){
return CFCopyLocalizedStringFromTableInBundle(key,_281,CFBundleGetMainBundle(),_282);
};
CFCopyLocalizedStringFromTableInBundle=function(key,_283,_284,_285){
return CFCopyLocalizedStringWithDefaultValue(key,_283,_284,null,_285);
};
CFCopyLocalizedStringWithDefaultValue=function(key,_286,_287,_288,_289){
var _28a;
if(!_286){
_286="Localizable";
}
_286+=".strings";
var _28b=_287._localizableStrings[_286];
_28a=_28b?_28b[key+_289]:null;
return _28a||(_288||key);
};
CFBundleGetMainBundle=function(){
return CFBundle.mainBundle();
};
var _28c={};
function _1cd(aURL,_28d,_28e,_28f,_290){
this._parent=_28d;
this._eventDispatcher=new _80(this);
var name=(aURL.absoluteURL()).lastPathComponent()||aURL.schemeAndAuthority();
this._name=name;
this._URL=aURL;
this._isResolved=!!_28f;
this._filenameTranslateDictionary=_290;
if(_28e){
this._URL=this._URL.asDirectoryPathURL();
}
if(!_28d){
_28c[name]=this;
}
this._isDirectory=!!_28e;
this._isNotFound=NO;
if(_28d){
_28d._children[name]=this;
}
if(_28e){
this._children={};
}else{
this._contents="";
}
};
_1cd.rootResources=function(){
return _28c;
};
function _291(x){
var _292=0;
for(var k in x){
if(x.hasOwnProperty(k)){
++_292;
}
}
return _292;
};
_1cd.resetRootResources=function(){
_28c={};
};
_1cd.prototype.filenameTranslateDictionary=function(){
return this._filenameTranslateDictionary||{};
};
_2.StaticResource=_1cd;
function _20c(_293){
_293._isResolved=YES;
_293._eventDispatcher.dispatchEvent({type:"resolve",staticResource:_293});
};
_1cd.prototype.resolve=function(){
if(this.isDirectory()){
var _294=new CFBundle(this.URL());
_294.onerror=function(){
};
_294.load(NO);
}else{
var self=this;
function _295(_296){
self._contents=_296.request.responseText();
_20c(self);
};
function _297(){
self._isNotFound=YES;
_20c(self);
};
var url=this.URL(),_298=this.filenameTranslateDictionary();
if(_298){
var _299=url.toString(),_29a=url.lastPathComponent(),_29b=_299.substring(0,_299.length-_29a.length),_29c=_298[_29a];
if(_29c&&_299.slice(-_29c.length)!==_29c){
url=new CFURL(_29b+_29c);
}
}
new _c1(url,_295,_297);
}
};
_1cd.prototype.name=function(){
return this._name;
};
_1cd.prototype.URL=function(){
return this._URL;
};
_1cd.prototype.contents=function(){
return this._contents;
};
_1cd.prototype.children=function(){
return this._children;
};
_1cd.prototype.parent=function(){
return this._parent;
};
_1cd.prototype.isResolved=function(){
return this._isResolved;
};
_1cd.prototype.write=function(_29d){
this._contents+=_29d;
};
function _29e(_29f){
var _2a0=_29f.schemeAndAuthority(),_2a1=_28c[_2a0];
if(!_2a1){
_2a1=new _1cd(new CFURL(_2a0),NULL,YES,YES);
}
return _2a1;
};
_1cd.resourceAtURL=function(aURL,_2a2){
aURL=(_1e4(aURL)).absoluteURL();
var _2a3=_29e(aURL),_2a4=aURL.pathComponents(),_a0=0,_2a5=_2a4.length;
for(;_a0<_2a5;++_a0){
var name=_2a4[_a0];
if(_85.call(_2a3._children,name)){
_2a3=_2a3._children[name];
}else{
if(_2a2){
if(name!=="/"){
name="./"+name;
}
_2a3=new _1cd(new CFURL(name,_2a3.URL()),_2a3,YES,YES);
}else{
throw new Error("Static Resource at "+aURL+" is not resolved (\""+name+"\")");
}
}
}
return _2a3;
};
_1cd.prototype.resourceAtURL=function(aURL,_2a6){
return _1cd.resourceAtURL(new CFURL(aURL,this.URL()),_2a6);
};
_1cd.resolveResourcesAtURLs=function(URLs,_2a7){
var _2a8=URLs.length,_2a9={};
for(var i=0,size=_2a8;i<size;i++){
var url=URLs[i];
_1cd.resolveResourceAtURL(url,NO,function(_2aa){
_2a9[url]=_2aa;
if(--_2a8===0){
_2a7(_2a9);
}
});
}
};
_1cd.resolveResourceAtURL=function(aURL,_2ab,_2ac,_2ad){
aURL=(_1e4(aURL)).absoluteURL();
_2ae(_29e(aURL),_2ab,aURL.pathComponents(),0,_2ac,_2ad);
};
_1cd.prototype.resolveResourceAtURL=function(aURL,_2af,_2b0){
_1cd.resolveResourceAtURL((new CFURL(aURL,this.URL())).absoluteURL(),_2af,_2b0);
};
function _2ae(_2b1,_2b2,_2b3,_2b4,_2b5,_2b6){
var _2b7=_2b3.length;
for(;_2b4<_2b7;++_2b4){
var name=_2b3[_2b4],_2b8=_85.call(_2b1._children,name)&&_2b1._children[name];
if(!_2b8){
_2b8=new _1cd(new CFURL(name,_2b1.URL()),_2b1,_2b4+1<_2b7||_2b2,NO,_2b6);
_2b8.resolve();
}
if(!_2b8.isResolved()){
return _2b8.addEventListener("resolve",function(){
_2ae(_2b1,_2b2,_2b3,_2b4,_2b5,_2b6);
});
}
if(_2b8.isNotFound()){
return _2b5(null,new Error("File not found: "+_2b3.join("/")));
}
if(_2b4+1<_2b7&&_2b8.isFile()){
return _2b5(null,new Error("File is not a directory: "+_2b3.join("/")));
}
_2b1=_2b8;
}
_2b5(_2b1);
};
function _2b9(aURL,_2ba,_2bb){
var _2bc=_1cd.includeURLs(),_2bd=(new CFURL(aURL,_2bc[_2ba])).absoluteURL();
_1cd.resolveResourceAtURL(_2bd,NO,function(_2be){
if(!_2be){
if(_2ba+1<_2bc.length){
_2b9(aURL,_2ba+1,_2bb);
}else{
_2bb(NULL);
}
return;
}
_2bb(_2be);
});
};
_1cd.resolveResourceAtURLSearchingIncludeURLs=function(aURL,_2bf){
_2b9(aURL,0,_2bf);
};
_1cd.prototype.addEventListener=function(_2c0,_2c1){
this._eventDispatcher.addEventListener(_2c0,_2c1);
};
_1cd.prototype.removeEventListener=function(_2c2,_2c3){
this._eventDispatcher.removeEventListener(_2c2,_2c3);
};
_1cd.prototype.isNotFound=function(){
return this._isNotFound;
};
_1cd.prototype.isFile=function(){
return !this._isDirectory;
};
_1cd.prototype.isDirectory=function(){
return this._isDirectory;
};
_1cd.prototype.toString=function(_2c4){
if(this.isNotFound()){
return "<file not found: "+this.name()+">";
}
var _2c5=this.name();
if(this.isDirectory()){
var _2c6=this._children;
for(var name in _2c6){
if(_2c6.hasOwnProperty(name)){
var _2c7=_2c6[name];
if(_2c4||!_2c7.isNotFound()){
_2c5+="\n\t"+((_2c6[name].toString(_2c4)).split("\n")).join("\n\t");
}
}
}
}
return _2c5;
};
var _2c8=NULL;
_1cd.includeURLs=function(){
if(_2c8!==NULL){
return _2c8;
}
_2c8=[];
if(!_1.OBJJ_INCLUDE_PATHS&&!_1.OBJJ_INCLUDE_URLS){
_2c8=["Frameworks","Frameworks/Debug"];
}else{
_2c8=(_1.OBJJ_INCLUDE_PATHS||[]).concat(_1.OBJJ_INCLUDE_URLS||[]);
}
var _2c9=_2c8.length;
while(_2c9--){
_2c8[_2c9]=(new CFURL(_2c8[_2c9])).asDirectoryPathURL();
}
return _2c8;
};
var _2ca="accessors",_2cb="class",_2cc="end",_2cd="function",_2ce="implementation",_2cf="import",_2d0="each",_2d1="outlet",_2d2="action",_2d3="new",_2d4="selector",_2d5="super",_2d6="var",_2d7="in",_2d8="pragma",_2d9="mark",_2da="=",_2db="+",_2dc="-",_2dd=":",_2de=",",_2df=".",_2e0="*",_2e1=";",_2e2="<",_2e3="{",_2e4="}",_2e5=">",_2e6="[",_2e7="\"",_2e8="@",_2e9="#",_2ea="]",_2eb="?",_2ec="(",_2ed=")",_2ee=/^(?:(?:\s+$)|(?:\/(?:\/|\*)))/,_2ef=/^[+-]?\d+(([.]\d+)*([eE][+-]?\d+))?$/,_2f0=/^[a-zA-Z_$](\w|$)*$/;
function _2f1(_2f2){
this._index=-1;
this._tokens=(_2f2+"\n").match(/\/\/.*(\r|\n)?|\/\*(?:.|\n|\r)*?\*\/|\w+\b|[+-]?\d+(([.]\d+)*([eE][+-]?\d+))?|"[^"\\]*(\\[\s\S][^"\\]*)*"|'[^'\\]*(\\[\s\S][^'\\]*)*'|\s+|./g);
this._context=[];
return this;
};
_2f1.prototype.push=function(){
this._context.push(this._index);
};
_2f1.prototype.pop=function(){
this._index=this._context.pop();
};
_2f1.prototype.peek=function(_2f3){
if(_2f3){
this.push();
var _2f4=this.skip_whitespace();
this.pop();
return _2f4;
}
return this._tokens[this._index+1];
};
_2f1.prototype.next=function(){
return this._tokens[++this._index];
};
_2f1.prototype.previous=function(){
return this._tokens[--this._index];
};
_2f1.prototype.last=function(){
if(this._index<0){
return NULL;
}
return this._tokens[this._index-1];
};
_2f1.prototype.skip_whitespace=function(_2f5){
var _2f6;
if(_2f5){
while((_2f6=this.previous())&&_2ee.test(_2f6)){
}
}else{
while((_2f6=this.next())&&_2ee.test(_2f6)){
}
}
return _2f6;
};
_2.Lexer=_2f1;
function _2f7(){
this.atoms=[];
};
_2f7.prototype.toString=function(){
return this.atoms.join("");
};
_2.preprocess=function(_2f8,aURL,_2f9){
return (new _2fa(_2f8,aURL,_2f9)).executable();
};
_2.eval=function(_2fb){
return eval((_2.preprocess(_2fb)).code());
};
var _2fa=function(_2fc,aURL,_2fd){
this._URL=new CFURL(aURL);
_2fc=_2fc.replace(/^#[^\n]+\n/,"\n");
this._currentSelector="";
this._currentClass="";
this._currentSuperClass="";
this._currentSuperMetaClass="";
this._buffer=new _2f7();
this._preprocessed=NULL;
this._dependencies=[];
this._tokens=new _2f1(_2fc);
this._flags=_2fd;
this._classMethod=false;
this._executable=NULL;
this._classLookupTable={};
this._classVars={};
var _2fe=new objj_class();
for(var i in _2fe){
this._classVars[i]=1;
}
this.preprocess(this._tokens,this._buffer);
};
_2fa.prototype.setClassInfo=function(_2ff,_300,_301){
this._classLookupTable[_2ff]={superClassName:_300,ivars:_301};
};
_2fa.prototype.getClassInfo=function(_302){
return this._classLookupTable[_302];
};
_2fa.prototype.allIvarNamesForClassName=function(_303){
var _304={},_305=this.getClassInfo(_303);
while(_305){
for(var i in _305.ivars){
_304[i]=1;
}
_305=this.getClassInfo(_305.superClassName);
}
return _304;
};
_2.Preprocessor=_2fa;
_2fa.Flags={};
_2fa.Flags.IncludeDebugSymbols=1<<0;
_2fa.Flags.IncludeTypeSignatures=1<<1;
_2fa.prototype.executable=function(){
if(!this._executable){
this._executable=new _306(this._buffer.toString(),this._dependencies,this._URL);
}
return this._executable;
};
_2fa.prototype.accessors=function(_307){
var _308=_307.skip_whitespace(),_309={};
if(_308!=_2ec){
_307.previous();
return _309;
}
while((_308=_307.skip_whitespace())!=_2ed){
var name=_308,_30a=true;
if(!/^ w+$/.test(name)){
throw new SyntaxError(this.error_message("*** @accessors attribute name not valid."));
}
if((_308=_307.skip_whitespace())==_2da){
_30a=_307.skip_whitespace();
if(!/^ w+$/.test(_30a)){
throw new SyntaxError(this.error_message("*** @accessors attribute value not valid."));
}
if(name=="setter"){
if((_308=_307.next())!=_2dd){
throw new SyntaxError(this.error_message("*** @accessors setter attribute requires argument with \":\" at end of selector name."));
}
_30a+=":";
}
_308=_307.skip_whitespace();
}
_309[name]=_30a;
if(_308==_2ed){
break;
}
if(_308!=_2de){
throw new SyntaxError(this.error_message("*** Expected ',' or ')' in @accessors attribute list."));
}
}
return _309;
};
_2fa.prototype.brackets=function(_30b,_30c){
var _30d=[];
while(this.preprocess(_30b,NULL,NULL,NULL,_30d[_30d.length]=[])){
}
if(_30d[0].length===1){
_30c.atoms[_30c.atoms.length]="[";
_30c.atoms[_30c.atoms.length]=_30d[0][0];
_30c.atoms[_30c.atoms.length]="]";
}else{
var _30e=new _2f7();
if(_30d[0][0].atoms[0]==_2d5){
_30c.atoms[_30c.atoms.length]="objj_msgSendSuper(";
_30c.atoms[_30c.atoms.length]="{ receiver:self, super_class:"+(this._classMethod?this._currentSuperMetaClass:this._currentSuperClass)+" }";
}else{
_30c.atoms[_30c.atoms.length]="objj_msgSend(";
_30c.atoms[_30c.atoms.length]=_30d[0][0];
}
_30e.atoms[_30e.atoms.length]=_30d[0][1];
var _30f=1,_310=_30d.length,_311=new _2f7();
for(;_30f<_310;++_30f){
var pair=_30d[_30f];
_30e.atoms[_30e.atoms.length]=pair[1];
_311.atoms[_311.atoms.length]=", "+pair[0];
}
_30c.atoms[_30c.atoms.length]=", \"";
_30c.atoms[_30c.atoms.length]=_30e;
_30c.atoms[_30c.atoms.length]="\"";
_30c.atoms[_30c.atoms.length]=_311;
_30c.atoms[_30c.atoms.length]=")";
}
};
_2fa.prototype.directive=function(_312,_313,_314){
var _315=_313?_313:new _2f7(),_316=_312.next();
if(_316.charAt(0)==_2e7){
_315.atoms[_315.atoms.length]=_316;
}else{
if(_316===_2cb){
_312.skip_whitespace();
return;
}else{
if(_316===_2ce){
this.implementation(_312,_315);
}else{
if(_316===_2cf){
this._import(_312);
}else{
if(_316===_2d4){
this.selector(_312,_315);
}
}
}
}
}
if(!_313){
return _315;
}
};
_2fa.prototype.hash=function(_317,_318){
var _319=_318?_318:new _2f7(),_31a=_317.next();
if(_31a===_2d8){
_31a=_317.skip_whitespace();
if(_31a===_2d9){
while((_31a=_317.next()).indexOf("\n")<0){
}
}
}else{
throw new SyntaxError(this.error_message("*** Expected \"pragma\" to follow # but instead saw \""+_31a+"\"."));
}
};
_2fa.prototype.implementation=function(_31b,_31c){
var _31d=_31c,_31e="",_31f=NO,_320=_31b.skip_whitespace(),_321="Nil",_322=new _2f7(),_323=new _2f7();
if(!/^\w/.test(_320)){
throw new Error(this.error_message("*** Expected class name, found \""+_320+"\"."));
}
this._currentSuperClass="objj_getClass(\""+_320+"\").super_class";
this._currentSuperMetaClass="objj_getMetaClass(\""+_320+"\").super_class";
this._currentClass=_320;
this._currentSelector="";
if((_31e=_31b.skip_whitespace())==_2ec){
_31e=_31b.skip_whitespace();
if(_31e==_2ed){
throw new SyntaxError(this.error_message("*** Can't Have Empty Category Name for class \""+_320+"\"."));
}
if(_31b.skip_whitespace()!=_2ed){
throw new SyntaxError(this.error_message("*** Improper Category Definition for class \""+_320+"\"."));
}
_31d.atoms[_31d.atoms.length]="{\nvar the_class = objj_getClass(\""+_320+"\")\n";
_31d.atoms[_31d.atoms.length]="if(!the_class) throw new SyntaxError(\"*** Could not find definition for class \\\""+_320+"\\\"\");\n";
_31d.atoms[_31d.atoms.length]="var meta_class = the_class.isa;";
}else{
if(_31e==_2dd){
_31e=_31b.skip_whitespace();
if(!_2f0.test(_31e)){
throw new SyntaxError(this.error_message("*** Expected class name, found \""+_31e+"\"."));
}
_321=_31e;
_31e=_31b.skip_whitespace();
}
_31d.atoms[_31d.atoms.length]="{var the_class = objj_allocateClassPair("+_321+", \""+_320+"\"),\nmeta_class = the_class.isa;";
if(_31e==_2e3){
var _324={},_325=0,_326=[],_327,_328={},_329=[];
while((_31e=_31b.skip_whitespace())&&_31e!=_2e4){
if(_31e===_2e8){
_31e=_31b.next();
if(_31e===_2ca){
_327=this.accessors(_31b);
}else{
if(_31e!==_2d1){
throw new SyntaxError(this.error_message("*** Unexpected '@' token in ivar declaration ('@"+_31e+"')."));
}else{
_329.push("@"+_31e);
}
}
}else{
if(_31e==_2e1){
if(_325++===0){
_31d.atoms[_31d.atoms.length]="class_addIvars(the_class, [";
}else{
_31d.atoms[_31d.atoms.length]=", ";
}
var name=_326[_326.length-1];
if(this._flags&_2fa.Flags.IncludeTypeSignatures){
_31d.atoms[_31d.atoms.length]="new objj_ivar(\""+name+"\", \""+(_329.slice(0,_329.length-1)).join(" ")+"\")";
}else{
_31d.atoms[_31d.atoms.length]="new objj_ivar(\""+name+"\")";
}
_324[name]=1;
_326=[];
_329=[];
if(_327){
_328[name]=_327;
_327=NULL;
}
}else{
_326.push(_31e);
_329.push(_31e);
}
}
}
if(_326.length){
throw new SyntaxError(this.error_message("*** Expected ';' in ivar declaration, found '}'."));
}
if(_325){
_31d.atoms[_31d.atoms.length]="]);\n";
}
if(!_31e){
throw new SyntaxError(this.error_message("*** Expected '}'"));
}
this.setClassInfo(_320,_321==="Nil"?null:_321,_324);
var _324=this.allIvarNamesForClassName(_320);
for(ivar_name in _328){
var _32a=_328[ivar_name],_32b=_32a["property"]||ivar_name;
var _32c=_32a["getter"]||_32b,_32d="(id)"+_32c+"\n{\nreturn "+ivar_name+";\n}";
if(_322.atoms.length!==0){
_322.atoms[_322.atoms.length]=",\n";
}
_322.atoms[_322.atoms.length]=this.method(new _2f1(_32d),_324);
if(_32a["readonly"]){
continue;
}
var _32e=_32a["setter"];
if(!_32e){
var _32f=_32b.charAt(0)=="_"?1:0;
_32e=(_32f?"_":"")+"set"+(_32b.substr(_32f,1)).toUpperCase()+_32b.substring(_32f+1)+":";
}
var _330="(void)"+_32e+"(id)newValue\n{\n";
if(_32a["copy"]){
_330+="if ("+ivar_name+" !== newValue)\n"+ivar_name+" = [newValue copy];\n}";
}else{
_330+=ivar_name+" = newValue;\n}";
}
if(_322.atoms.length!==0){
_322.atoms[_322.atoms.length]=",\n";
}
_322.atoms[_322.atoms.length]=this.method(new _2f1(_330),_324);
}
}else{
_31b.previous();
}
_31d.atoms[_31d.atoms.length]="objj_registerClassPair(the_class);\n";
}
if(!_324){
var _324=this.allIvarNamesForClassName(_320);
}
while(_31e=_31b.skip_whitespace()){
if(_31e==_2db){
this._classMethod=true;
if(_323.atoms.length!==0){
_323.atoms[_323.atoms.length]=", ";
}
_323.atoms[_323.atoms.length]=this.method(_31b,this._classVars);
}else{
if(_31e==_2dc){
this._classMethod=false;
if(_322.atoms.length!==0){
_322.atoms[_322.atoms.length]=", ";
}
_322.atoms[_322.atoms.length]=this.method(_31b,_324);
}else{
if(_31e==_2e9){
this.hash(_31b,_31d);
}else{
if(_31e==_2e8){
if((_31e=_31b.next())==_2cc){
break;
}else{
throw new SyntaxError(this.error_message("*** Expected \"@end\", found \"@"+_31e+"\"."));
}
}
}
}
}
}
if(_322.atoms.length!==0){
_31d.atoms[_31d.atoms.length]="class_addMethods(the_class, [";
_31d.atoms[_31d.atoms.length]=_322;
_31d.atoms[_31d.atoms.length]="]);\n";
}
if(_323.atoms.length!==0){
_31d.atoms[_31d.atoms.length]="class_addMethods(meta_class, [";
_31d.atoms[_31d.atoms.length]=_323;
_31d.atoms[_31d.atoms.length]="]);\n";
}
_31d.atoms[_31d.atoms.length]="}";
this._currentClass="";
};
_2fa.prototype._import=function(_331){
var _332="",_333=_331.skip_whitespace(),_334=_333!==_2e2;
if(_333===_2e2){
while((_333=_331.next())&&_333!==_2e5){
_332+=_333;
}
if(!_333){
throw new SyntaxError(this.error_message("*** Unterminated import statement."));
}
}else{
if(_333.charAt(0)===_2e7){
_332=_333.substr(1,_333.length-2);
}else{
throw new SyntaxError(this.error_message("*** Expecting '<' or '\"', found \""+_333+"\"."));
}
}
this._buffer.atoms[this._buffer.atoms.length]="objj_executeFile(\"";
this._buffer.atoms[this._buffer.atoms.length]=_332;
this._buffer.atoms[this._buffer.atoms.length]=_334?"\", YES);":"\", NO);";
this._dependencies.push(new _335(new CFURL(_332),_334));
};
_2fa.prototype.method=function(_336,_337){
var _338=new _2f7(),_339,_33a="",_33b=[],_33c=[null];
_337=_337||{};
while((_339=_336.skip_whitespace())&&_339!==_2e3&&_339!==_2e1){
if(_339==_2dd){
var type="";
_33a+=_339;
_339=_336.skip_whitespace();
if(_339==_2ec){
while((_339=_336.skip_whitespace())&&_339!=_2ed){
type+=_339;
}
_339=_336.skip_whitespace();
}
_33c[_33b.length+1]=type||null;
_33b[_33b.length]=_339;
if(_339 in _337){
CPLog.warn(this.error_message("*** Warning: Method ( "+_33a+" ) uses a parameter name that is already in use ( "+_339+" )"));
}
}else{
if(_339==_2ec){
var type="";
while((_339=_336.skip_whitespace())&&_339!=_2ed){
type+=_339;
}
_33c[0]=type||null;
}else{
if(_339==_2de){
if((_339=_336.skip_whitespace())!=_2df||_336.next()!=_2df||_336.next()!=_2df){
throw new SyntaxError(this.error_message("*** Argument list expected after ','."));
}
}else{
_33a+=_339;
}
}
}
}
if(_339===_2e1){
_339=_336.skip_whitespace();
if(_339!==_2e3){
throw new SyntaxError(this.error_message("Invalid semi-colon in method declaration. "+"Semi-colons are allowed only to terminate the method signature, before the open brace."));
}
}
var _33d=0,_33e=_33b.length;
_338.atoms[_338.atoms.length]="new objj_method(sel_getUid(\"";
_338.atoms[_338.atoms.length]=_33a;
_338.atoms[_338.atoms.length]="\"), function";
this._currentSelector=_33a;
if(this._flags&_2fa.Flags.IncludeDebugSymbols){
_338.atoms[_338.atoms.length]=" $"+this._currentClass+"__"+_33a.replace(/:/g,"_");
}
_338.atoms[_338.atoms.length]="(self, _cmd";
for(;_33d<_33e;++_33d){
_338.atoms[_338.atoms.length]=", ";
_338.atoms[_338.atoms.length]=_33b[_33d];
}
_338.atoms[_338.atoms.length]=")\n{ with(self)\n{";
_338.atoms[_338.atoms.length]=this.preprocess(_336,NULL,_2e4,_2e3);
_338.atoms[_338.atoms.length]="}\n}";
if(this._flags&_2fa.Flags.IncludeDebugSymbols){
_338.atoms[_338.atoms.length]=","+JSON.stringify(_33c);
}
_338.atoms[_338.atoms.length]=")";
this._currentSelector="";
return _338;
};
_2fa.prototype.preprocess=function(_33f,_340,_341,_342,_343){
var _344=_340?_340:new _2f7(),_345=0,_346="";
if(_343){
_343[0]=_344;
var _347=false,_348=[0,0,0];
}
while((_346=_33f.next())&&(_346!==_341||_345)){
if(_343){
if(_346===_2eb){
++_348[2];
}else{
if(_346===_2e3){
++_348[0];
}else{
if(_346===_2e4){
--_348[0];
}else{
if(_346===_2ec){
++_348[1];
}else{
if(_346===_2ed){
--_348[1];
}else{
if((_346===_2dd&&_348[2]--===0||(_347=_346===_2ea))&&_348[0]===0&&_348[1]===0){
_33f.push();
var _349=_347?_33f.skip_whitespace(true):_33f.previous(),_34a=_2ee.test(_349);
if(_34a||_2f0.test(_349)&&_2ee.test(_33f.previous())){
_33f.push();
var last=_33f.skip_whitespace(true),_34b=true,_34c=false;
if(last==="+"||last==="-"){
if(_33f.previous()!==last){
_34b=false;
}else{
last=_33f.skip_whitespace(true);
_34c=true;
}
}
_33f.pop();
_33f.pop();
if(_34b&&(!_34c&&last===_2e4||last===_2ed||last===_2ea||last===_2df||_2ef.test(last)||last.charAt(last.length-1)==="\""||last.charAt(last.length-1)==="'"||_2f0.test(last)&&!/^(new|return|case|var)$/.test(last))){
if(_34a){
_343[1]=":";
}else{
_343[1]=_349;
if(!_347){
_343[1]+=":";
}
var _345=_344.atoms.length;
while(_344.atoms[_345--]!==_349){
}
_344.atoms.length=_345;
}
return !_347;
}
if(_347){
return NO;
}
}
_33f.pop();
if(_347){
return NO;
}
}
}
}
}
}
}
_348[2]=MAX(_348[2],0);
}
if(_342){
if(_346===_342){
++_345;
}else{
if(_346===_341){
--_345;
}
}
}
if(_346===_2cd){
var _34d="";
while((_346=_33f.next())&&_346!==_2ec&&!/^\w/.test(_346)){
_34d+=_346;
}
if(_346===_2ec){
if(_342===_2ec){
++_345;
}
_344.atoms[_344.atoms.length]="function"+_34d+"(";
if(_343){
++_348[1];
}
}else{
_344.atoms[_344.atoms.length]=_346+" = function";
}
}else{
if(_346==_2e8){
this.directive(_33f,_344);
}else{
if(_346==_2e9){
this.hash(_33f,_344);
}else{
if(_346==_2e6){
this.brackets(_33f,_344);
}else{
_344.atoms[_344.atoms.length]=_346;
}
}
}
}
}
if(_343){
throw new SyntaxError(this.error_message("*** Expected ']' - Unterminated message send or array."));
}
if(!_340){
return _344;
}
};
_2fa.prototype.selector=function(_34e,_34f){
var _350=_34f?_34f:new _2f7();
_350.atoms[_350.atoms.length]="sel_getUid(\"";
if(_34e.skip_whitespace()!=_2ec){
throw new SyntaxError(this.error_message("*** Expected '('"));
}
var _351=_34e.skip_whitespace();
if(_351==_2ed){
throw new SyntaxError(this.error_message("*** Unexpected ')', can't have empty @selector()"));
}
_34f.atoms[_34f.atoms.length]=_351;
var _352,_353=true;
while((_352=_34e.next())&&_352!=_2ed){
if(_353&&/^\d+$/.test(_352)||!/^(\w|$|\:)/.test(_352)){
if(!/\S/.test(_352)){
if(_34e.skip_whitespace()==_2ed){
break;
}else{
throw new SyntaxError(this.error_message("*** Unexpected whitespace in @selector()."));
}
}else{
throw new SyntaxError(this.error_message("*** Illegal character '"+_352+"' in @selector()."));
}
}
_350.atoms[_350.atoms.length]=_352;
_353=_352==_2dd;
}
_350.atoms[_350.atoms.length]="\")";
if(!_34f){
return _350;
}
};
_2fa.prototype.error_message=function(_354){
return _354+" <Context File: "+this._URL+(this._currentClass?" Class: "+this._currentClass:"")+(this._currentSelector?" Method: "+this._currentSelector:"")+">";
};
(function(_355,walk){
"use strict";
_355.version="0.3.3-objj-3";
var _356,_357,_358,_359;
_355.parse=function(inpt,opts){
_357=String(inpt);
_358=_357.length;
_35a(opts);
_35b();
if(_356.macros){
_35c(_356.macros);
}
_35d();
return _35e(_356.program);
};
var _35f=_355.defaultOptions={ecmaVersion:5,strictSemicolons:false,allowTrailingCommas:true,forbidReserved:false,trackComments:false,trackCommentsIncludeLineBreak:false,trackSpaces:false,locations:false,onComment:null,ranges:false,program:null,sourceFile:null,objj:true,preprocess:true,preprocessGetIncludeFile:_360,preprocessAddMacro:_361,preprocessGetMacro:_362,preprocessUndefineMacro:_363,preprocessIsMacro:_364,macros:null,lineNoInErrorMessage:true,preIncludeFiles:null};
function _35a(opts){
_356=opts||{};
for(var opt in _35f){
if(!Object.prototype.hasOwnProperty.call(_356,opt)){
_356[opt]=_35f[opt];
}
}
_359=_356.sourceFile||null;
};
var _365;
var _366;
var _367=function(name,_368,_369){
return new _36a(name,_368,null,_369-name.length);
};
var _36b={1:function(){
return _367("__OBJJ__",_356.objj?"1":null,_36c);
}};
_36b["__"+"BROWSER"+"__"]=function(){
return _367("__BROWSER__",typeof window!=="undefined"?"1":null,_36c);
};
_36b["__"+"LINE"+"__"]=function(){
return _367("__LINE__",String(_356.locations?_36d:(_36e(_357,_36c)).line),_36c);
};
_36b["__"+"DATE"+"__"]=function(){
var date,day;
return _367("__DATE__",(date=new Date(),day=String(date.getDate()),["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][date.getMonth()]+(day.length>1?" ":"  ")+day+" "+date.getFullYear()),_36c);
};
_36b["__"+"TIME"+"__"]=function(){
var date;
return _367("__TIME__",(date=new Date(),("0"+date.getHours()).slice(-2)+":"+("0"+date.getMinutes()).slice(-2)+":"+("0"+date.getSeconds()).slice(-2)),_36c);
};
function _360(_36f){
return {include:"#define FOO(x) x\n",sourceFile:_36f};
};
function _361(_370){
_365[_370.identifier]=_370;
_366=null;
};
function _362(_371){
return _365[_371];
};
function _363(_372){
delete _365[_372];
_366=null;
};
function _364(_373){
return (_366||(_366=_374(((Object.keys(_365)).concat((Object.keys(_36b)).filter(function(key){
return (this[key]()).macro!=null;
},_36b))).join(" "))))(_373);
};
function _375(_376){
var _377=_36b[_376];
return _377?_377():null;
};
function _35c(_378){
for(var i=0,size=_378.length;i<size;i++){
var _379=_357;
var _37a=_378[i].trim();
var pos=_37a.indexOf("=");
if(pos===0){
_37b(0,"Invalid macro definition: '"+_37a+"'");
}
var name,body;
if(pos>0){
name=_37a.slice(0,pos);
body=_37a.slice(pos+1);
}else{
name=_37a;
}
if(_36b.hasOwnProperty(name)){
_37b(0,"'"+name+"' is a predefined macro name");
}
_357=name+(body!=null?" "+body:"");
_358=_357.length;
_35d();
_37c();
_357=_379;
_358=_357.length;
}
};
var _36e=_355.getLineInfo=function(_37d,_37e){
for(var line=1,cur=0;;){
_37f.lastIndex=cur;
var _380=_37f.exec(_37d);
if(_380&&_380.index<_37e){
++line;
cur=_380.index+_380[0].length;
}else{
break;
}
}
return {line:line,column:_37e-cur,lineStart:cur,lineEnd:_380?_380.index+_380[0].length:_37d.length};
};
_355.tokenize=function(inpt,opts){
_357=String(inpt);
_358=_357.length;
_35a(opts);
_35d();
_35b();
var t={};
function _381(_382){
_457(_382);
t.start=_38a;
t.end=_38b;
t.startLoc=_392;
t.endLoc=_393;
t.type=_394;
t.value=_395;
return t;
};
_381.jumpTo=function(pos,_383){
_36c=pos;
if(_356.locations){
_36d=1;
_384=_37f.lastIndex=0;
var _385;
while((_385=_37f.exec(_357))&&_385.index<pos){
++_36d;
_384=_385.index+_385[0].length;
}
}
_386=_383;
_387();
};
return _381;
};
var _36c;
var _388,_389,_38a,_38b,_38c,_38d,_38e;
var _38f;
var _390,_391;
var _392,_393;
var _394,_395;
var _396,_397,_398;
var _399,_39a,_39b;
var _386,_39c,_39d;
var _36d,_384;
var _39e,_39f,_3a0;
var _3a1,_3a2,_3a3;
var _3a4;
var _3a5,_3a6,_3a7;
var _3a8,_3a9,_3aa,_3ab,_3ac;
var _3ad,_3ae;
var _3af;
var _3b0;
var _3b1;
var _3b2;
var _3b3;
var _3b4;
var _3b5;
var _3b6;
var _3b7;
var _3b8;
var _3b9;
var _3ba;
function _37b(pos,_3bb){
if(typeof pos=="number"){
pos=_36e(_357,pos);
}
if(_356.lineNoInErrorMessage){
_3bb+=" ("+pos.line+":"+pos.column+")";
}
var _3bc=new SyntaxError(_3bb);
_3bc.messageOnLine=pos.line;
_3bc.messageOnColumn=pos.column;
_3bc.lineStart=pos.lineStart;
_3bc.lineEnd=pos.lineEnd;
_3bc.fileName=_359;
throw _3bc;
};
var _3bd=[];
var _3be={type:"num"},_3bf={type:"regexp"},_3c0={type:"string"};
var _3c1={type:"name"},_3c2={type:"eof"},_3c3={type:"eol"};
var _3c4={keyword:"break"},_3c5={keyword:"case",beforeExpr:true},_3c6={keyword:"catch"};
var _3c7={keyword:"continue"},_3c8={keyword:"debugger"},_3c9={keyword:"default"};
var _3ca={keyword:"do",isLoop:true},_3cb={keyword:"else",beforeExpr:true};
var _3cc={keyword:"finally"},_3cd={keyword:"for",isLoop:true},_3ce={keyword:"function"};
var _3cf={keyword:"if"},_3d0={keyword:"return",beforeExpr:true},_3d1={keyword:"switch"};
var _3d2={keyword:"throw",beforeExpr:true},_3d3={keyword:"try"},_3d4={keyword:"var"};
var _3d5={keyword:"while",isLoop:true},_3d6={keyword:"with"},_3d7={keyword:"new",beforeExpr:true};
var _3d8={keyword:"this"};
var _3d9={keyword:"void",prefix:true,beforeExpr:true};
var _3da={keyword:"null",atomValue:null},_3db={keyword:"true",atomValue:true};
var _3dc={keyword:"false",atomValue:false};
var _3dd={keyword:"in",binop:7,beforeExpr:true};
var _3de={keyword:"implementation"},_3df={keyword:"outlet"},_3e0={keyword:"accessors"};
var _3e1={keyword:"end"},_3e2={keyword:"import"};
var _3e3={keyword:"action"},_3e4={keyword:"selector"},_3e5={keyword:"class"},_3e6={keyword:"global"};
var _3e7={keyword:"{"},_3e8={keyword:"["};
var _3e9={keyword:"ref"},_3ea={keyword:"deref"};
var _3eb={keyword:"protocol"},_3ec={keyword:"optional"},_3ed={keyword:"required"};
var _3ee={keyword:"interface"};
var _3ef={keyword:"typedef"};
var _3f0={keyword:"filename"},_3f1={keyword:"unsigned",okAsIdent:true},_3f2={keyword:"signed",okAsIdent:true};
var _3f3={keyword:"byte",okAsIdent:true},_3f4={keyword:"char",okAsIdent:true},_3f5={keyword:"short",okAsIdent:true};
var _3f6={keyword:"int",okAsIdent:true},_3f7={keyword:"long",okAsIdent:true},_3f8={keyword:"id",okAsIdent:true};
var _3f9={keyword:"BOOL",okAsIdent:true},_3fa={keyword:"SEL",okAsIdent:true},_3fb={keyword:"float",okAsIdent:true};
var _3fc={keyword:"double",okAsIdent:true};
var _3fd={keyword:"#"};
var _3fe={keyword:"define"};
var _3ff={keyword:"undef"};
var _400={keyword:"ifdef"};
var _401={keyword:"ifndef"};
var _402={keyword:"if"};
var _403={keyword:"else"};
var _404={keyword:"endif"};
var _405={keyword:"elif"};
var _406={keyword:"elif (True)"};
var _407={keyword:"elif (false)"};
var _408={keyword:"pragma"};
var _409={keyword:"defined"};
var _40a={keyword:"\\"};
var _40b={keyword:"error"};
var _40c={keyword:"warning"};
var _40d={type:"preprocessParamItem"};
var _40e={type:"skipLine"};
var _40f={keyword:"include"};
var _410={"break":_3c4,"case":_3c5,"catch":_3c6,"continue":_3c7,"debugger":_3c8,"default":_3c9,"do":_3ca,"else":_3cb,"finally":_3cc,"for":_3cd,"function":_3ce,"if":_3cf,"return":_3d0,"switch":_3d1,"throw":_3d2,"try":_3d3,"var":_3d4,"while":_3d5,"with":_3d6,"null":_3da,"true":_3db,"false":_3dc,"new":_3d7,"in":_3dd,"instanceof":{keyword:"instanceof",binop:7,beforeExpr:true},"this":_3d8,"typeof":{keyword:"typeof",prefix:true,beforeExpr:true},"void":_3d9,"delete":{keyword:"delete",prefix:true,beforeExpr:true}};
var _411={"IBAction":_3e3,"IBOutlet":_3df,"unsigned":_3f1,"signed":_3f2,"byte":_3f3,"char":_3f4,"short":_3f5,"int":_3f6,"long":_3f7,"id":_3f8,"float":_3fb,"BOOL":_3f9,"SEL":_3fa,"double":_3fc};
var _412={"implementation":_3de,"outlet":_3df,"accessors":_3e0,"end":_3e1,"import":_3e2,"action":_3e3,"selector":_3e4,"class":_3e5,"global":_3e6,"ref":_3e9,"deref":_3ea,"protocol":_3eb,"optional":_3ec,"required":_3ed,"interface":_3ee,"typedef":_3ef};
var _413={"define":_3fe,"pragma":_408,"ifdef":_400,"ifndef":_401,"undef":_3ff,"if":_402,"endif":_404,"else":_403,"elif":_405,"defined":_409,"warning":_40c,"error":_40b,"include":_40f};
var _414={type:"[",beforeExpr:true},_415={type:"]"},_416={type:"{",beforeExpr:true};
var _417={type:"}"},_418={type:"(",beforeExpr:true},_419={type:")"};
var _41a={type:",",beforeExpr:true},_41b={type:";",beforeExpr:true};
var _41c={type:":",beforeExpr:true},_41d={type:"."},_41e={type:"?",beforeExpr:true};
var _41f={type:"@"},_420={type:"..."},_421={type:"#"};
var _422={binop:10,beforeExpr:true,preprocess:true},_423={isAssign:true,beforeExpr:true,preprocess:true};
var _424={isAssign:true,beforeExpr:true},_425={binop:9,prefix:true,beforeExpr:true,preprocess:true};
var _426={postfix:true,prefix:true,isUpdate:true},_427={prefix:true,beforeExpr:true,preprocess:true};
var _428={binop:1,beforeExpr:true,preprocess:true},_429={binop:2,beforeExpr:true,preprocess:true};
var _42a={binop:3,beforeExpr:true,preprocess:true},_42b={binop:4,beforeExpr:true,preprocess:true};
var _42c={binop:5,beforeExpr:true,preprocess:true},_42d={binop:6,beforeExpr:true,preprocess:true};
var _42e={binop:7,beforeExpr:true,preprocess:true},_42f={binop:8,beforeExpr:true,preprocess:true};
var _430={binop:10,beforeExpr:true,preprocess:true};
_355.tokTypes={bracketL:_414,bracketR:_415,braceL:_416,braceR:_417,parenL:_418,parenR:_419,comma:_41a,semi:_41b,colon:_41c,dot:_41d,question:_41e,slash:_422,eq:_423,name:_3c1,eof:_3c2,num:_3be,regexp:_3bf,string:_3c0};
for(var kw in _410){
_355.tokTypes["_"+kw]=_410[kw];
}
function _374(_431){
_431=_431.split(" ");
var f="",cats=[];
out:
for(var i=0;i<_431.length;++i){
for(var j=0;j<cats.length;++j){
if(cats[j][0].length==_431[i].length){
cats[j].push(_431[i]);
continue out;
}
}
cats.push([_431[i]]);
}
function _432(arr){
if(arr.length==1){
return f+="return str === "+JSON.stringify(arr[0])+";";
}
f+="switch(str){";
for(var i=0;i<arr.length;++i){
f+="case "+JSON.stringify(arr[i])+":";
}
f+="return true}return false;";
};
if(cats.length>3){
cats.sort(function(a,b){
return b.length-a.length;
});
f+="switch(str.length){";
for(var i=0;i<cats.length;++i){
var cat=cats[i];
f+="case "+cat[0].length+":";
_432(cat);
}
f+="}";
}else{
_432(_431);
}
return new Function("str",f);
};
_355.makePredicate=_374;
var _433=_374("abstract boolean byte char class double enum export extends final float goto implements import int interface long native package private protected public short static super synchronized throws transient volatile");
var _434=_374("class enum extends super const export import");
var _435=_374("implements interface let package private protected public static yield");
var _436=_374("eval arguments");
var _437=_374("break case catch continue debugger default do else finally for function if return switch throw try var while with null true false instanceof typeof void delete new in this");
var _438=_374("IBAction IBOutlet byte char short int long float unsigned signed id BOOL SEL double");
var _439=_374("define undef pragma if ifdef ifndef else elif endif defined error warning include");
var _43a=/[\u1680\u180e\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]/;
var _43b=/[\u1680\u180e\u2000-\u200a\u202f\u205f\u3000\ufeff]/;
var _43c="ªµºÀ-ÖØ-öø-ˁˆ-ˑˠ-ˤˬˮͰ-ʹͶͷͺ-ͽΆΈ-ΊΌΎ-ΡΣ-ϵϷ-ҁҊ-ԧԱ-Ֆՙա-ևא-תװ-ײؠ-يٮٯٱ-ۓەۥۦۮۯۺ-ۼۿܐܒ-ܯݍ-ޥޱߊ-ߪߴߵߺࠀ-ࠕࠚࠤࠨࡀ-ࡘࢠࢢ-ࢬऄ-हऽॐक़-ॡॱ-ॷॹ-ॿঅ-ঌএঐও-নপ-রলশ-হঽৎড়ঢ়য়-ৡৰৱਅ-ਊਏਐਓ-ਨਪ-ਰਲਲ਼ਵਸ਼ਸਹਖ਼-ੜਫ਼ੲ-ੴઅ-ઍએ-ઑઓ-નપ-રલળવ-હઽૐૠૡଅ-ଌଏଐଓ-ନପ-ରଲଳଵ-ହଽଡ଼ଢ଼ୟ-ୡୱஃஅ-ஊஎ-ஐஒ-கஙசஜஞடணதந-பம-ஹௐఅ-ఌఎ-ఐఒ-నప-ళవ-హఽౘౙౠౡಅ-ಌಎ-ಐಒ-ನಪ-ಳವ-ಹಽೞೠೡೱೲഅ-ഌഎ-ഐഒ-ഺഽൎൠൡൺ-ൿඅ-ඖක-නඳ-රලව-ෆก-ะาำเ-ๆກຂຄງຈຊຍດ-ທນ-ຟມ-ຣລວສຫອ-ະາຳຽເ-ໄໆໜ-ໟༀཀ-ཇཉ-ཬྈ-ྌက-ဪဿၐ-ၕၚ-ၝၡၥၦၮ-ၰၵ-ႁႎႠ-ჅჇჍა-ჺჼ-ቈቊ-ቍቐ-ቖቘቚ-ቝበ-ኈኊ-ኍነ-ኰኲ-ኵኸ-ኾዀዂ-ዅወ-ዖዘ-ጐጒ-ጕጘ-ፚᎀ-ᎏᎠ-Ᏼᐁ-ᙬᙯ-ᙿᚁ-ᚚᚠ-ᛪᛮ-ᛰᜀ-ᜌᜎ-ᜑᜠ-ᜱᝀ-ᝑᝠ-ᝬᝮ-ᝰក-ឳៗៜᠠ-ᡷᢀ-ᢨᢪᢰ-ᣵᤀ-ᤜᥐ-ᥭᥰ-ᥴᦀ-ᦫᧁ-ᧇᨀ-ᨖᨠ-ᩔᪧᬅ-ᬳᭅ-ᭋᮃ-ᮠᮮᮯᮺ-ᯥᰀ-ᰣᱍ-ᱏᱚ-ᱽᳩ-ᳬᳮ-ᳱᳵᳶᴀ-ᶿḀ-ἕἘ-Ἕἠ-ὅὈ-Ὅὐ-ὗὙὛὝὟ-ώᾀ-ᾴᾶ-ᾼιῂ-ῄῆ-ῌῐ-ΐῖ-Ίῠ-Ῥῲ-ῴῶ-ῼⁱⁿₐ-ₜℂℇℊ-ℓℕℙ-ℝℤΩℨK-ℭℯ-ℹℼ-ℿⅅ-ⅉⅎⅠ-ↈⰀ-Ⱞⰰ-ⱞⱠ-ⳤⳫ-ⳮⳲⳳⴀ-ⴥⴧⴭⴰ-ⵧⵯⶀ-ⶖⶠ-ⶦⶨ-ⶮⶰ-ⶶⶸ-ⶾⷀ-ⷆⷈ-ⷎⷐ-ⷖⷘ-ⷞⸯ々-〇〡-〩〱-〵〸-〼ぁ-ゖゝ-ゟァ-ヺー-ヿㄅ-ㄭㄱ-ㆎㆠ-ㆺㇰ-ㇿ㐀-䶵一-鿌ꀀ-ꒌꓐ-ꓽꔀ-ꘌꘐ-ꘟꘪꘫꙀ-ꙮꙿ-ꚗꚠ-ꛯꜗ-ꜟꜢ-ꞈꞋ-ꞎꞐ-ꞓꞠ-Ɦꟸ-ꠁꠃ-ꠅꠇ-ꠊꠌ-ꠢꡀ-ꡳꢂ-ꢳꣲ-ꣷꣻꤊ-ꤥꤰ-ꥆꥠ-ꥼꦄ-ꦲꧏꨀ-ꨨꩀ-ꩂꩄ-ꩋꩠ-ꩶꩺꪀ-ꪯꪱꪵꪶꪹ-ꪽꫀꫂꫛ-ꫝꫠ-ꫪꫲ-ꫴꬁ-ꬆꬉ-ꬎꬑ-ꬖꬠ-ꬦꬨ-ꬮꯀ-ꯢ가-힣ힰ-ퟆퟋ-ퟻ豈-舘並-龎ﬀ-ﬆﬓ-ﬗיִײַ-ﬨשׁ-זּטּ-לּמּנּסּףּפּצּ-ﮱﯓ-ﴽﵐ-ﶏﶒ-ﷇﷰ-ﷻﹰ-ﹴﹶ-ﻼＡ-Ｚａ-ｚｦ-ﾾￂ-ￇￊ-ￏￒ-ￗￚ-ￜ";
var _43d="̀-ͯ҃-֑҇-ׇֽֿׁׂׅׄؐ-ؚؠ-ىٲ-ۓۧ-ۨۻ-ۼܰ-݊ࠀ-ࠔࠛ-ࠣࠥ-ࠧࠩ-࠭ࡀ-ࡗࣤ-ࣾऀ-ःऺ-़ा-ॏ॑-ॗॢ-ॣ०-९ঁ-ঃ়া-ৄেৈৗয়-ৠਁ-ਃ਼ਾ-ੂੇੈੋ-੍ੑ੦-ੱੵઁ-ઃ઼ા-ૅે-ૉો-્ૢ-ૣ૦-૯ଁ-ଃ଼ା-ୄେୈୋ-୍ୖୗୟ-ୠ୦-୯ஂா-ூெ-ைொ-்ௗ௦-௯ఁ-ఃె-ైొ-్ౕౖౢ-ౣ౦-౯ಂಃ಼ಾ-ೄೆ-ೈೊ-್ೕೖೢ-ೣ೦-೯ംഃെ-ൈൗൢ-ൣ൦-൯ංඃ්ා-ුූෘ-ෟෲෳิ-ฺเ-ๅ๐-๙ິ-ູ່-ໍ໐-໙༘༙༠-༩༹༵༷ཁ-ཇཱ-྄྆-྇ྍ-ྗྙ-ྼ࿆က-ဩ၀-၉ၧ-ၭၱ-ၴႂ-ႍႏ-ႝ፝-፟ᜎ-ᜐᜠ-ᜰᝀ-ᝐᝲᝳក-ឲ៝០-៩᠋-᠍᠐-᠙ᤠ-ᤫᤰ-᤻ᥑ-ᥭᦰ-ᧀᧈ-ᧉ᧐-᧙ᨀ-ᨕᨠ-ᩓ᩠-᩿᩼-᪉᪐-᪙ᭆ-ᭋ᭐-᭙᭫-᭳᮰-᮹᯦-᯳ᰀ-ᰢ᱀-᱉ᱛ-ᱽ᳐-᳒ᴀ-ᶾḁ-ἕ‌‍‿⁀⁔⃐-⃥⃜⃡-⃰ⶁ-ⶖⷠ-ⷿ〡-〨゙゚Ꙁ-ꙭꙴ-꙽ꚟ꛰-꛱ꟸ-ꠀ꠆ꠋꠣ-ꠧꢀ-ꢁꢴ-꣄꣐-꣙ꣳ-ꣷ꤀-꤉ꤦ-꤭ꤰ-ꥅꦀ-ꦃ꦳-꧀ꨀ-ꨧꩀ-ꩁꩌ-ꩍ꩐-꩙ꩻꫠ-ꫩꫲ-ꫳꯀ-ꯡ꯬꯭꯰-꯹ﬠ-ﬨ︀-️︠-︦︳︴﹍-﹏０-９＿";
var _43e=new RegExp("["+_43c+"]");
var _43f=new RegExp("["+_43c+_43d+"]");
var _440=/[\n\r\u2028\u2029]/;
var _37f=/\r\n|[\n\r\u2028\u2029]/g;
var _441=_355.isIdentifierStart=function(code){
if(code<65){
return code===36;
}
if(code<91){
return true;
}
if(code<97){
return code===95;
}
if(code<123){
return true;
}
return code>=170&&_43e.test(String.fromCharCode(code));
};
var _442=_355.isIdentifierChar=function(code){
if(code<48){
return code===36;
}
if(code<58){
return true;
}
if(code<65){
return false;
}
if(code<91){
return true;
}
if(code<97){
return code===95;
}
if(code<123){
return true;
}
return code>=170&&_43f.test(String.fromCharCode(code));
};
function _443(){
this.line=_36d;
this.column=_36c-_384;
if(_3b0){
var _444=_3b0.macro;
var _445=_444.locationOffset;
if(_445){
var _446=_445.line;
if(_446){
this.line+=_446;
}
var _447=_445.column;
if(_447){
this.column+=_38d-(_36d===0?_447:0);
}
}
}
};
function _448(line,_449){
this.line=line;
this.column=_449;
if(_3b0){
var _44a=_3b0.macro;
var _44b=_44a.locationOffset;
if(_44b){
var _44c=_44b.line;
if(_44c){
this.line+=_44c;
}
var _44d=_44b.column;
if(_44d){
this.column+=_44d;
}
}
}
};
function _35d(){
_36d=1;
_36c=_384=_38e=_38c=_38d=0;
_386=true;
_39c=null;
_39d=null;
_387();
};
function _35b(){
_365=Object.create(null);
_366=null;
_3b4=null;
_3b5=null;
_3b2=false;
_3b3=false;
_3af=[];
_3b0=null;
_3b1=null;
_3b7=false;
_3b9=true;
_3b8=false;
_3ba=[];
};
function _44e(type,val,_44f){
if(_44f){
_389=_38b=_44f;
if(_356.locations){
_393=preprocessOverrideTokLoc;
}
}else{
_389=_38b=_36c;
if(_356.locations){
_393=new _443();
}
}
_394=type;
var ch=_387();
if(ch===35&&_356.preprocess&&_357.charCodeAt(_36c+1)===35){
var val1=val!=null?val:type.keyword||type.type;
_36c+=2;
if(val1!=null){
var _450=_356.locations&&new _448(_36d,_384);
var _451=_39e,_452=_38b,_453=_38a,_454=_38a+_38c,_455=_3b0&&_3b0.macro&&_3b0.macro.variadicName;
_387();
if(_455&&_455===_357.slice(_36c,_36c+_455.length)){
var _456=true;
}
_3b8=true;
_457(null,2);
_3b8=false;
var val2=_395!=null?_395:_394.keyword||_394.type;
if(val2!=null){
if(_456&&val1===","&&val2===""){
return _457();
}
var _458=""+val1+val2,_459=_38a+_38d;
var _45a=new _36a(null,_458,null,_454,false,null,false,_450);
var r=_45b(_45a,_38d,_3b0?_3b0.parameterDict:null,null,_36c,next,null);
if(_3b0&&_3b0.macro===_45a){
_394=type;
_38a=_453;
_38b=_452;
_39e=_451;
_38d=_459-val1.length;
if(!_456){
console.log("Warning: pasting formed '"+_458+"', an invalid preprocessing token");
}
}else{
return r;
}
}
}
}
_395=val;
_398=_397;
_39b=_39a;
_397=_39c;
_39a=_39d;
_386=type.beforeExpr;
};
function _45c(_45d,_45e){
var _45f=_356.onComment&&_356.locations&&new _443();
var _460=_36c,end=_357.indexOf("*/",_36c+=2);
if(end===-1){
_37b(_36c-2,"Unterminated comment");
}
_36c=end+2;
if(_356.locations){
_37f.lastIndex=_460;
var _461;
while((_461=_37f.exec(_357))&&_461.index<_36c){
++_36d;
_384=_461.index+_461[0].length;
}
}
if(!_45e){
if(_356.onComment){
_356.onComment(true,_357.slice(_460+2,end),_460,_36c,_45f,_356.locations&&new _443());
}
if(_356.trackComments){
(_39c||(_39c=[])).push(_357.slice(_45d!=null&&_356.trackCommentsIncludeLineBreak?_45d:_460,_36c));
}
}
};
function _462(_463,_464){
var _465=_36c;
var _466=_356.onComment&&_356.locations&&new _443();
var ch=_357.charCodeAt(_36c+=2);
while(_36c<_358&&ch!==10&&ch!==13&&ch!==8232&&ch!==8233){
++_36c;
ch=_357.charCodeAt(_36c);
}
if(!_464){
if(_356.onComment){
_356.onComment(false,_357.slice(_465+2,_36c),_465,_36c,_466,_356.locations&&new _443());
}
if(_356.trackComments){
(_39c||(_39c=[])).push(_357.slice(_463!=null&&_356.trackCommentsIncludeLineBreak?_463:_465,_36c));
}
}
};
function _467(){
var ch=_357.charCodeAt(_36c);
var last;
while(_36c<_358&&(ch!==10&&ch!==13&&ch!==8232&&ch!==8233||last===92)){
if(ch!=32&&ch!=9&&ch!=160&&(ch<5760||!_43b.test(String.fromCharCode(ch)))){
last=ch;
}
ch=_357.charCodeAt(++_36c);
}
if(_356.locations){
++_36d;
_384=_36c;
}
};
function _387(){
_39c=null;
_39d=null;
return _468();
};
function _468(_469,_46a,_46b){
var _46c=_36c,_46d,ch;
for(;;){
ch=_357.charCodeAt(_36c);
if(ch===32){
++_36c;
}else{
if(ch===13){
if(_469){
break;
}
_46d=_36c;
++_36c;
var next=_357.charCodeAt(_36c);
if(next===10){
++_36c;
}
if(_356.locations){
++_36d;
_384=_36c;
}
}else{
if(ch===10){
if(_469){
break;
}
_46d=_36c;
++_36c;
if(_356.locations){
++_36d;
_384=_36c;
}
}else{
if(ch===9){
++_36c;
}else{
if(ch===47){
if(_46b){
break;
}
var next=_357.charCodeAt(_36c+1);
if(next===42){
if(_356.trackSpaces){
(_39d||(_39d=[])).push(_357.slice(_46c,_36c));
}
_45c(_46d);
_46c=_36c;
}else{
if(next===47){
if(_356.trackSpaces){
(_39d||(_39d=[])).push(_357.slice(_46c,_36c));
}
_462(_46d);
_46c=_36c;
}else{
break;
}
}
}else{
if(ch===160||ch===11||ch===12||ch>=5760&&_43a.test(String.fromCharCode(ch))){
++_36c;
}else{
if(_36c>=_358){
if(_356.preprocess){
if(_46a){
return true;
}
if(!_3af.length){
break;
}
if(_390==null){
_390=_36c;
}
var _46e=_3af.pop();
var _46f=_357;
var _470=_359;
_36c=_46e.end;
_357=_46e.input;
_358=_46e.inputLen;
_36d=_46e.currentLine;
_384=_46e.currentLineStart;
_3b1=_46e.onlyTransformArgumentsForLastToken;
_3b4=_46e.parameterScope;
_38d=_46e.macroOffset;
_359=_46e.sourceFile;
_389=_46e.lastEnd;
var _471=_3af.length;
_3b0=_471?_3af[_471-1]:null;
return _468(_469);
}else{
break;
}
}else{
if(ch===92){
if(!_356.preprocess){
break;
}
var pos=_36c+1;
ch=_357.charCodeAt(pos);
while(pos<_358&&(ch===32||ch===9||ch===11||ch===12||ch>=5760&&_43b.test(String.fromCharCode(ch)))){
ch=_357.charCodeAt(++pos);
}
_37f.lastIndex=0;
var _472=_37f.exec(_357.slice(pos,pos+2));
if(_472&&_472.index===0){
_36c=pos+_472[0].length;
if(_356.locations){
++_36d;
_384=_36c;
}
}else{
break;
}
}else{
break;
}
}
}
}
}
}
}
}
}
return ch;
};
function _473(code,_474){
var next=_357.charCodeAt(_36c+1);
if(next>=48&&next<=57){
return _475(String.fromCharCode(code),_474);
}
if(next===46&&_356.objj&&_357.charCodeAt(_36c+2)===46){
_36c+=3;
return _474(_420);
}
++_36c;
return _474(_41d);
};
function _476(_477){
var next=_357.charCodeAt(_36c+1);
if(_386){
++_36c;
return _478();
}
if(next===61){
return _479(_424,2,_477);
}
return _479(_422,1,_477);
};
function _47a(_47b){
var next=_357.charCodeAt(_36c+1);
if(next===61){
return _479(_424,2,_47b);
}
return _479(_430,1,_47b);
};
function _47c(code,_47d){
var next=_357.charCodeAt(_36c+1);
if(next===code){
return _479(code===124?_428:_429,2,_47d);
}
if(next===61){
return _479(_424,2,_47d);
}
return _479(code===124?_42a:_42c,1,_47d);
};
function _47e(_47f){
var next=_357.charCodeAt(_36c+1);
if(next===61){
return _479(_424,2,_47f);
}
return _479(_42b,1,_47f);
};
function _480(code,_481){
var next=_357.charCodeAt(_36c+1);
if(next===code){
return _479(_426,2,_481);
}
if(next===61){
return _479(_424,2,_481);
}
return _479(_425,1,_481);
};
function _482(code,_483){
if(code===60&&(_394===_3e2||_3a9===_40f)&&_356.objj){
for(var _484=_36c+1;;){
var ch=_357.charCodeAt(++_36c);
if(ch===62){
return _483(_3f0,_357.slice(_484,_36c++));
}
if(_36c>=_358||ch===13||ch===10||ch===8232||ch===8233){
_37b(_38a,"Unterminated import statement");
}
}
}
var next=_357.charCodeAt(_36c+1);
var size=1;
if(next===code){
size=code===62&&_357.charCodeAt(_36c+2)===62?3:2;
if(_357.charCodeAt(_36c+size)===61){
return _479(_424,size+1,_483);
}
return _479(_42f,size,_483);
}
if(next===61){
size=_357.charCodeAt(_36c+2)===61?3:2;
}
return _479(_42e,size,_483);
};
function _485(code,_486){
var next=_357.charCodeAt(_36c+1);
if(next===61){
return _479(_42d,_357.charCodeAt(_36c+2)===61?3:2,_486);
}
return _479(code===61?_423:_427,1,_486);
};
function _487(code,_488){
var next=_357.charCodeAt(++_36c);
if(next===34||next===39){
return _489(next,_488);
}
if(next===123){
return _488(_3e7);
}
if(next===91){
return _488(_3e8);
}
var word=_48a(),_48b=_412[word];
if(!_48b){
_37b(_38a,"Unrecognized Objective-J keyword '@"+word+"'");
}
return _488(_48b);
};
function _48c(_48d){
++_36c;
_48e();
_48f(false,true);
switch(_3a9){
case _3fe:
if(_3b9){
_37c();
}else{
return _48d(_3fe);
}
break;
case _3ff:
_48f();
_356.preprocessUndefineMacro(_490());
break;
case _402:
if(_3b9){
var _491=_386;
_386=false;
_3ba.push(_402);
_48f(false,false,true);
var expr=_492(true);
var test=_493(expr);
if(!test){
_3b9=false;
_494();
}
_386=_491;
}else{
return _48d(_402);
}
break;
case _400:
if(_3b9){
_3ba.push(_402);
_48f();
var _495=_490();
var test=_356.preprocessIsMacro(_495);
if(!test){
_3b9=false;
_494();
}
}else{
return _48d(_400);
}
break;
case _401:
if(_3b9){
_3ba.push(_402);
_48f();
var _495=_490();
var test=_356.preprocessIsMacro(_495);
if(test){
_3b9=false;
_494();
}
}else{
return _48d(_401);
}
break;
case _403:
if(_3ba.length){
if(_3b9){
if(_3ba[_3ba.length-1]===_402){
_3ba[_3ba.length-1]=_403;
_3b9=false;
_48d(_403);
_48f();
_494(true);
}else{
_37b(_3ab,"#else after #else");
}
}else{
_3ba[_3ba.length-1]=_403;
return _48d(_403);
}
}else{
_37b(_3ab,"#else without #if");
}
break;
case _405:
if(_3ba.length){
if(_3b9){
if(_3ba[_3ba.length-1]===_402){
_3b9=false;
_48d(_405);
_48f();
_494(true);
}else{
_37b(_3ab,"#elsif after #else");
}
}else{
var _491=_386;
_386=false;
_3b9=true;
_48f(false,false,true);
var expr=_492(true);
_3b9=false;
_386=_491;
var test=_493(expr);
return _48d(test?_406:_407);
}
}else{
_37b(_3ab,"#elif without #if");
}
break;
case _404:
if(_3ba.length){
if(_3b9){
_3ba.pop();
break;
}
}else{
_37b(_3ab,"#endif without #if");
}
return _48d(_404);
break;
case _408:
_467();
break;
case _427:
_467();
break;
case _40c:
_48f(false,false,true);
var expr=_492();
console.log("Warning: "+String(_493(expr)));
break;
case _40b:
var _496=_3ab;
_48f(false,false,true);
var expr=_492();
_37b(_496,"Error: "+String(_493(expr)));
break;
case _40f:
if(!_3b9){
return _48d(_40f);
}
_48f();
if(_3a9===_3c0){
var _497=true;
}else{
if(_3a9===_3f0){
var _497=false;
}else{
_37b(_3ab,"Expected \"FILENAME\" or <FILENAME>: "+(_3a9.keyword||_3a9.type));
}
}
var _498=_3aa;
var _499=_356.preprocessGetIncludeFile(_3aa,_497)||_37b(_3ab,"'"+_498+"' file not found");
var _49a=_499.include;
var _49b=new _36a(null,_49a,null,0,false,null,false,null,_499.sourceFile);
_49c(_3fd,null,null,true);
_49d(_49b,_49b.macro,_38d,null,null,_36c,null,true);
_387();
_457(null,null,true);
return;
break;
default:
if(_3b0){
if(_3b0.parameterDict&&_3b0.macro.isParameterFunction()(_3aa)){
var _49e=_3b0.parameterDict[_3aa];
if(_49e){
return _44e(_3c0,_49e.macro);
}
}
}
_37b(_3ab,"Invalid preprocessing directive");
_467();
return _48d(_3fd);
}
if(_3a9===_3c3&&_356.trackSpaces){
if(_39d&&_39d.length){
_39d.push("\n"+_39d.pop());
}else{
_39d=["\n"];
}
}
_49c(_3a9,null,null,true);
return next(true);
};
function _37c(){
_3b3=true;
_48f();
var _49f=_3ac;
_3b7=true;
var _4a0=_490();
if(_357.charCodeAt(_49f)===40){
_4a1(_418);
var _4a2=[];
var _4a3=false;
var _4a4=true;
while(!_4a5(_419)){
if(_4a3){
_37b(_3ab,"Variadic parameter must be last");
}
if(!_4a4){
_4a1(_41a,"Expected ',' between macro parameters");
}else{
_4a4=false;
}
_4a2.push(_4a5(_420)?_4a3=true&&"__VA_ARGS__":_490());
if(_4a5(_420)){
_4a3=true;
}
}
}
var _4a6=_3ab;
var _4a7=_356.locations&&new _448(_36d,_384);
while(_3a9!==_3c3&&_3a9!==_3c2){
_48f();
}
_3b7=false;
var _4a8=_39f.slice(_4a6,_3ab);
_4a8=_4a8.replace(/\\/g," ");
_356.preprocessAddMacro(new _36a(_4a0,_4a8,_4a2,_4a6,false,null,_4a3&&_4a2[_4a2.length-1],_4a7));
_3b3=false;
};
function _493(expr){
return walk.recursive(expr,{},{LogicalExpression:function(node,st,c){
var left=node.left,_4a9=node.right;
switch(node.operator){
case "||":
return c(left,st)||c(_4a9,st);
case "&&":
return c(left,st)&&c(_4a9,st);
}
},BinaryExpression:function(node,st,c){
var left=node.left,_4aa=node.right;
switch(node.operator){
case "+":
return c(left,st)+c(_4aa,st);
case "-":
return c(left,st)-c(_4aa,st);
case "*":
return c(left,st)*c(_4aa,st);
case "/":
return c(left,st)/c(_4aa,st);
case "%":
return c(left,st)%c(_4aa,st);
case "<":
return c(left,st)<c(_4aa,st);
case ">":
return c(left,st)>c(_4aa,st);
case "^":
return c(left,st)^c(_4aa,st);
case "&":
return c(left,st)&c(_4aa,st);
case "|":
return c(left,st)|c(_4aa,st);
case "==":
return c(left,st)==c(_4aa,st);
case "===":
return c(left,st)===c(_4aa,st);
case "!=":
return c(left,st)!=c(_4aa,st);
case "!==":
return c(left,st)!==c(_4aa,st);
case "<=":
return c(left,st)<=c(_4aa,st);
case ">=":
return c(left,st)>=c(_4aa,st);
case ">>":
return c(left,st)>>c(_4aa,st);
case ">>>":
return c(left,st)>>>c(_4aa,st);
case "<<":
return c(left,st)<<c(_4aa,st);
}
},UnaryExpression:function(node,st,c){
var arg=node.argument;
switch(node.operator){
case "-":
return -c(arg,st);
case "+":
return +c(arg,st);
case "!":
return !c(arg,st);
case "~":
return ~c(arg,st);
}
},Literal:function(node,st,c){
return node.value;
},Identifier:function(node,st,c){
return 0;
},DefinedExpression:function(node,st,c){
var _4ab=node.object;
if(_4ab.type==="Identifier"){
var name=_4ab.name,_4ac=_356.preprocessGetMacro(name)||_375(name);
return _4ac||0;
}else{
return c(_4ab,st);
}
}},{});
};
function _4ad(code,_4ae,_4af){
switch(code){
case 46:
return _473(code,_4ae);
case 40:
++_36c;
return _4ae(_418);
case 41:
++_36c;
return _4ae(_419);
case 59:
++_36c;
return _4ae(_41b);
case 44:
++_36c;
return _4ae(_41a);
case 91:
++_36c;
return _4ae(_414);
case 93:
++_36c;
return _4ae(_415);
case 123:
++_36c;
return _4ae(_416);
case 125:
++_36c;
return _4ae(_417);
case 58:
++_36c;
return _4ae(_41c);
case 63:
++_36c;
return _4ae(_41e);
case 48:
var next=_357.charCodeAt(_36c+1);
if(next===120||next===88){
return _4b0(_4ae);
}
case 49:
case 50:
case 51:
case 52:
case 53:
case 54:
case 55:
case 56:
case 57:
return _475(false,_4ae);
case 34:
case 39:
return _489(code,_4ae);
case 47:
return _476(_4ae);
case 37:
case 42:
return _47a(_4ae);
case 124:
case 38:
return _47c(code,_4ae);
case 94:
return _47e(_4ae);
case 43:
case 45:
return _480(code,_4ae);
case 60:
case 62:
return _482(code,_4ae);
case 61:
case 33:
return _485(code,_4ae);
case 126:
return _479(_427,1,_4ae);
case 64:
if(_356.objj){
return _487(code,_4ae);
}
return false;
case 35:
if(_356.preprocess){
if(_3b3){
++_36c;
return _4ae(_3fd);
}
_37f.lastIndex=0;
var _4b1=_37f.exec(_357.slice(_38f,_36c));
if(_3a2!==0&&_3a2!==_36c&&!_4b1&&(_3b0&&!_3b0.isIncludeFile||_36c!==0)){
if(_3b0){
return _4b2();
}else{
_37b(_36c,"Preprocessor directives may only be used at the beginning of a line");
}
}
return _48c(_4ae);
}
return false;
case 92:
if(_356.preprocess){
return _479(_40a,1,_4ae);
}
return false;
}
if(_4af){
var r;
if(code===13){
r=_479(_3c3,_357.charCodeAt(_36c+1)===10?2:1,_4ae);
}else{
if(code===10||code===8232||code===8233){
r=_479(_3c3,1,_4ae);
}else{
return false;
}
}
if(_356.locations){
++_36d;
_384=_36c;
}
return r;
}
return false;
};
function _4b2(){
var _4b3=_3af.length,_4b4=_3b0;
_36c++;
_3b8=true;
next(false,2);
_3b8=false;
var _4b5=_38a+_38c;
var _4b6=_356.locations&&new _448(_36d,_384);
var _4b7;
if(_394===_3c0){
var _4b8=_39e.slice(_38a,_38a+1);
var _4b9=_4b8==="\""?"\\\"":"'";
_4b7=_4b9;
_4b7+=_4ba(_395);
_4b7+=_4b9;
}else{
_4b7=_395!=null?_395:_394.keyword||_394.type;
}
while(_3af.length>_4b3&&_4b4===_3af[_4b3-1]){
_3b8=true;
next(false,2);
_3b8=false;
if(_3a2!==_38a){
_4b7+=" ";
}
if(_394===_3c0){
var _4b8=_39e.slice(_38a,_38a+1);
var _4b9=_4b8==="\""?"\\\"":"'";
_4b7+=_4b9;
_4b7+=_4ba(_395);
_4b7+=_4b9;
}else{
_4b7+=_395!=null?_395:_394.keyword||_394.type;
}
}
var _4bb=new _36a(null,"\""+_4b7+"\"",null,_4b5,false,null,false,_4b6);
return _45b(_4bb,_38d,null,null,_36c,next);
};
function _4ba(_4bc){
for(var _4bd="",pos=0,size=_4bc.length,ch=_4bc.charCodeAt(pos);pos<size;ch=_4bc.charCodeAt(++pos)){
switch(ch){
case 34:
_4bd+="\\\\\\\"";
break;
case 10:
_4bd+="\\\\n";
break;
case 13:
_4bd+="\\\\r";
break;
case 9:
_4bd+="\\\\t";
break;
case 8:
_4bd+="\\\\b";
break;
case 11:
_4bd+="\\\\v";
break;
case 160:
_4bd+="\\\\u00A0";
break;
case 8232:
_4bd+="\\\\u2028";
break;
case 8233:
_4bd+="\\\\u2029";
break;
case 92:
_4bd+="\\\\";
break;
default:
_4bd+=_4bc.charAt(pos);
break;
}
}
return _4bd;
};
function _48e(_4be,_4bf){
var ch=_468(!_4bf);
return ch;
};
function _494(_4c0){
var _4c1=[];
while(_4c1.length>0||_3a9!==_404&&(_3a9!==_403&&_3a9!==_406||_4c0)){
switch(_3a9){
case _402:
case _400:
case _401:
_4c1.push(_402);
break;
case _403:
if(_4c1[_4c1.length-1]!==_402){
_37b(_3ab,"#else after #else");
}else{
_4c1[_4c1.length-1]=_403;
}
break;
case _405:
if(_4c1[_4c1.length-1]!==_402){
_37b(_3ab,"#elif after #else");
}
break;
case _404:
_4c1.pop();
break;
case _3c2:
_3b9=true;
_37b(_3ab,"Missing #endif");
}
_48f(true);
}
_3b9=true;
if(_3a9===_404){
_3ba.pop();
}
};
function _48f(_4c2,_4c3,_4c4,_4c5){
_3ab=_36c;
_39f=_357;
_3b5=_3b4;
if(_36c>=_358){
return _49c(_3c2);
}
var code=_357.charCodeAt(_36c);
if(!_4c3&&!_3b9&&code!==35){
_467();
return _49c(_40e,_357.slice(_3ab,_36c++));
}else{
if(_3b2&&code!==41&&code!==44){
var _4c6=0;
while(_36c<_358&&(_4c6||code!==41&&code!==44)){
if(code===40){
_4c6++;
}
if(code===41){
_4c6--;
}
if(code===34||code===39){
var _4c7=code;
code=_357.charCodeAt(++_36c);
while(_36c<_358&&code!==_4c7){
if(code===92){
code=_357.charCodeAt(++_36c);
if(code!==_4c7){
continue;
}
}
code=_357.charCodeAt(++_36c);
}
}
code=_357.charCodeAt(++_36c);
}
return _49c(_40d,_357.slice(_3ab,_36c));
}
}
if(_441(code)||code===92&&_357.charCodeAt(_36c+1)===117){
return _4c8(_4c4);
}
if(_4ad(code,_4c2?_4c9:_49c,true)===false){
var ch=String.fromCharCode(code);
if(ch==="\\"||_43e.test(ch)){
return _4c8(_4c4);
}
_37b(_36c,"Unexpected character '"+ch+"'");
}
};
function _4c8(_4ca,_4cb){
var word=_48a();
var type=_3c1;
if(_4ca&&_356.preprocess){
var _4cc=_4cd(word,_4ce,_4cb);
if(_4cc===true){
return true;
}
}
if(!_4cf&&_439(word)){
type=_413[word];
}
_49c(type,word,_4cc,false,_4ca);
};
function _49c(type,val,_4d0,_4d1,_4d2){
_3a9=type;
_3aa=val;
_3ac=_4d0||_36c;
if(type!==_3c3){
_389=_3ac;
}
var ch=_48e(false,_4d1);
if(ch===35&&_356.preprocess&&!_3b7&&_357.charCodeAt(_36c+1)===35){
var val1=val!=null?val:type.keyword||type.type;
_36c+=2;
if(val1!=null){
var _4d3=_356.locations&&new _448(_36d,_384);
var _4d4=_39e,_4d5=_3ac,_4d6=_3ab,_4d7=_3ab+_38c,_4d8=_3b0&&_3b0.macro&&_3b0.macro.variadicName;
_387();
if(_4d8&&_4d8===_357.slice(_36c,_36c+_4d8.length)){
var _4d9=true;
}
_3b8=true;
_48f(null,null,_4d2,2);
_3b8=false;
var val2=_3aa!=null?_3aa:_3a9.keyword||_3a9.type;
if(val2!=null){
if(_4d9&&val1===","&&val2===""){
return _48f();
}
var _4da=""+val1+val2,_4db=_3ab+_38d;
var _4dc=new _36a(null,_4da,null,_4d7,false,null,false,_4d3);
var r=_45b(_4dc,_38d,_3b0?_3b0.parameterDict:null,null,_36c,_4ce,null);
if(_3b0&&_3b0.macro===_4dc){
_3a9=type;
_3ab=_4d6;
_3ac=_4d5;
_39e=_4d4;
_38d=_4db-val1.length;
if(!_4d9){
console.log("Warning: pasting formed '"+_4da+"', an invalid preprocessing token");
}
}else{
return r;
}
}
}
}
};
function _4c9(type,val){
_3a9=type;
_3aa=val;
_389=_3ac=_36c;
_48e(true);
};
function _4ce(_4dd,_4de,_4df,_4e0){
if(!_4dd){
_3ad=_3ab;
_3ae=_3ac;
}
_38f=_389;
return _48f(false,false,_4e0,_4de);
};
function _4a5(type,_4e1){
if(_3a9===type){
_4ce(false,false,null,_4e1);
return true;
}
};
function _4a1(type,_4e2,_4e3){
if(_3a9===type){
_4ce(false,_32,null,_4e3);
}else{
_37b(_3ab,_4e2||"Unexpected token");
}
};
function _4e4(){
};
function _490(_4e5){
var _4e6=_3a9===_3c1?_3aa:(!_356.forbidReserved||_3a9.okAsIdent)&&_3a9.keyword||_4e4();
_4ce(false,false,null,_4e5);
return _4e6;
};
function _4e7(_4e8){
var node=_4e9();
node.name=_490(_4e8);
return _4ea(node,"Identifier");
};
function _492(_4eb){
return _4ec(_4eb);
};
function _4ec(_4ed){
return _4ee(_4ef(_4ed),-1,_4ed);
};
function _4ee(left,_4f0,_4f1){
var prec=_3a9.binop;
if(prec){
if(!_3a9.preprocess){
_37b(_3ab,"Unsupported macro operator");
}
if(prec>_4f0){
var node=_4f2(left);
node.left=left;
node.operator=_3aa;
_4ce(false,false,null,_4f1);
node.right=_4ee(_4ef(_4f1),prec,_4f1);
var node=_4ea(node,/&&|\|\|/.test(node.operator)?"LogicalExpression":"BinaryExpression");
return _4ee(node,_4f0,_4f1);
}
}
return left;
};
function _4ef(_4f3){
if(_3a9.preprocess&&_3a9.prefix){
var node=_4e9();
node.operator=_3aa;
node.prefix=true;
_4ce(false,false,null,_4f3);
node.argument=_4ef(_4f3);
return _4ea(node,"UnaryExpression");
}
return _4f4(_4f3);
};
function _4f4(_4f5){
switch(_3a9){
case _3c1:
return _4e7(_4f5);
case _3be:
case _3c0:
return _4f6(_4f5);
case _418:
var _4f7=_3ab;
_4ce(false,false,null,_4f5);
var val=_492(_4f5);
val.start=_4f7;
val.end=_3ac;
_4a1(_419,"Expected closing ')' in macro expression",_4f5);
return val;
case _409:
var node=_4e9();
_4ce(false,false,null,_4f5);
node.object=_4f8(_4f5);
return _4ea(node,"DefinedExpression");
default:
_4f9();
}
};
function _4f8(_4fa){
switch(_3a9){
case _3c1:
return _4e7(_4fa);
case _3be:
case _3c0:
return _4f6(_4fa);
case _418:
var _4fb=_3ab;
_4ce(false,false,null,_4fa);
var val=_4f8(_4fa);
val.start=_4fb;
val.end=_3ac;
_4a1(_419,"Expected closing ')' in macro expression",_4fa);
return val;
default:
_4f9();
}
};
function _4f6(_4fc){
var node=_4e9();
node.value=_3aa;
node.raw=_39f.slice(_3ab,_3ac);
_4ce(false,false,null,_4fc);
return _4ea(node,"Literal");
};
function _4ea(node,type){
node.type=type;
node.end=_3ae;
return node;
};
function _457(_4fd,_4fe,_4ff){
_396=_39c;
_399=_39d;
if(!_4fd){
_38a=_36c;
}else{
_36c=_38a+1;
}
if(!_4ff){
_388=_38a;
}
_39e=_357;
_38c=_38d;
_3b5=_3b4;
if(_356.locations){
_392=new _443();
}
if(_4fd){
return _478();
}
if(_36c>=_358){
return _44e(_3c2);
}
var code=_357.charCodeAt(_36c);
if(_441(code)||code===92){
return _500(null,_4fe,_4fd);
}
var tok=_4ad(code,_44e);
if(tok===false){
var ch=String.fromCharCode(code);
if(ch==="\\"||_43e.test(ch)){
return _500(null,_4fe,_4fd);
}
_37b(_36c,"Unexpected character '"+ch+"'");
}
return tok;
};
function _479(type,size,_501){
var str=_357.slice(_36c,_36c+size);
_36c+=size;
_501(type,str);
};
function _478(){
var _502="",_503,_504,_505=_36c;
for(;;){
if(_36c>=_358){
_37b(_505,"Unterminated regular expression");
}
var ch=_357.charAt(_36c);
if(_440.test(ch)){
_37b(_505,"Unterminated regular expression");
}
if(!_503){
if(ch==="["){
_504=true;
}else{
if(ch==="]"&&_504){
_504=false;
}else{
if(ch==="/"&&!_504){
break;
}
}
}
_503=ch==="\\";
}else{
_503=false;
}
++_36c;
}
var _502=_357.slice(_505,_36c);
++_36c;
var mods=_48a();
if(mods&&!/^[gmsiy]*$/.test(mods)){
_37b(_505,"Invalid regexp flag");
}
return _44e(_3bf,new RegExp(_502,mods));
};
function _506(_507,len){
var _508=_36c,_509=0;
for(var i=0,e=len==null?Infinity:len;i<e;++i){
var code=_357.charCodeAt(_36c),val;
if(code>=97){
val=code-97+10;
}else{
if(code>=65){
val=code-65+10;
}else{
if(code>=48&&code<=57){
val=code-48;
}else{
val=Infinity;
}
}
}
if(val>=_507){
break;
}
++_36c;
_509=_509*_507+val;
}
if(_36c===_508||len!=null&&_36c-_508!==len){
return null;
}
return _509;
};
function _4b0(_50a){
_36c+=2;
var val=_506(16);
if(val==null){
_37b(_38a+2,"Expected hexadecimal number");
}
if(_441(_357.charCodeAt(_36c))){
_37b(_36c,"Identifier directly after number");
}
return _50a(_3be,val);
};
function _475(_50b,_50c){
var _50d=_36c,_50e=false,_50f=_357.charCodeAt(_36c)===48;
if(!_50b&&_506(10)===null){
_37b(_50d,"Invalid number");
}
if(_357.charCodeAt(_36c)===46){
++_36c;
_506(10);
_50e=true;
}
var next=_357.charCodeAt(_36c);
if(next===69||next===101){
next=_357.charCodeAt(++_36c);
if(next===43||next===45){
++_36c;
}
if(_506(10)===null){
_37b(_50d,"Invalid number");
}
_50e=true;
}
if(_441(_357.charCodeAt(_36c))){
_37b(_36c,"Identifier directly after number");
}
var str=_357.slice(_50d,_36c),val;
if(_50e){
val=parseFloat(str);
}else{
if(!_50f||str.length===1){
val=parseInt(str,10);
}else{
if(/[89]/.test(str)||_3a7){
_37b(_50d,"Invalid number");
}else{
val=parseInt(str,8);
}
}
}
return _50c(_3be,val);
};
function _489(_510,_511){
_36c++;
var out="";
for(;;){
if(_36c>=_358){
_37b(_38a,"Unterminated string constant");
}
var ch=_357.charCodeAt(_36c);
if(ch===_510){
++_36c;
return _511(_3c0,out);
}
if(ch===92){
ch=_357.charCodeAt(++_36c);
var _512=/^[0-7]+/.exec(_357.slice(_36c,_36c+3));
if(_512){
_512=_512[0];
}
while(_512&&parseInt(_512,8)>255){
_512=_512.slice(0,_512.length-1);
}
if(_512==="0"){
_512=null;
}
++_36c;
if(_512){
if(_3a7){
_37b(_36c-2,"Octal literal in strict mode");
}
out+=String.fromCharCode(parseInt(_512,8));
_36c+=_512.length-1;
}else{
switch(ch){
case 110:
out+="\n";
break;
case 114:
out+="\r";
break;
case 120:
out+=String.fromCharCode(_513(2));
break;
case 117:
out+=String.fromCharCode(_513(4));
break;
case 85:
out+=String.fromCharCode(_513(8));
break;
case 116:
out+="\t";
break;
case 98:
out+="\b";
break;
case 118:
out+="\v";
break;
case 102:
out+="\f";
break;
case 48:
out+="\x00";
break;
case 13:
if(_357.charCodeAt(_36c)===10){
++_36c;
}
case 10:
if(_356.locations){
_384=_36c;
++_36d;
}
break;
default:
out+=String.fromCharCode(ch);
break;
}
}
}else{
if(ch===13||ch===10||ch===8232||ch===8233){
_37b(_38a,"Unterminated string constant");
}
out+=String.fromCharCode(ch);
++_36c;
}
}
};
function _513(len){
var n=_506(16,len);
if(n===null){
_37b(_38a,"Bad character escape sequence");
}
return n;
};
var _4cf;
function _48a(){
_4cf=false;
var word,_514=true,_515=_36c;
for(;;){
var ch=_357.charCodeAt(_36c);
if(_442(ch)){
if(_4cf){
word+=_357.charAt(_36c);
}
++_36c;
}else{
if(ch===92){
if(!_4cf){
word=_357.slice(_515,_36c);
}
_4cf=true;
if(_357.charCodeAt(++_36c)!=117){
_37b(_36c,"Expecting Unicode escape sequence \\uXXXX");
}
++_36c;
var esc=_513(4);
var _516=String.fromCharCode(esc);
if(!_516){
_37b(_36c-1,"Invalid Unicode escape");
}
if(!(_514?_441(esc):_442(esc))){
_37b(_36c-4,"Invalid Unicode escape");
}
word+=_516;
}else{
break;
}
}
_514=false;
}
return _4cf?word:_357.slice(_515,_36c);
};
function _500(_517,_518,_519){
var word=_517||_48a();
var type=_3c1;
if(_356.preprocess){
var _51a=_4cd(word,next,_518,_519);
if(_51a===true){
return true;
}
}
if(!_4cf){
if(_437(word)){
type=_410[word];
}else{
if(_356.objj&&_438(word)){
type=_411[word];
}else{
if(_356.forbidReserved&&(_356.ecmaVersion===3?_433:_434)(word)||_3a7&&_435(word)){
_37b(_38a,"The keyword '"+word+"' is reserved");
}
}
}
}
return _44e(type,word,_51a);
};
function _4cd(word,_51b,_51c,_51d){
var _51e,_51f=_3b0,_520=_3b4;
if(_51f){
var _521=_3b5||_3b0;
if(_521.parameterDict&&_521.macro.isParameterFunction()(word)){
_51e=_521.parameterDict[word];
if(!_51e&&_521.macro.variadicName===word){
if(_3b8){
_44e(_3c1,"");
return true;
}else{
_468();
_51b(true,_51c,_51d,true);
}
return true;
}
if(_468(true,true)===true){
if(_522(35,35)){
_51c=2;
}
}else{
if(_357.charCodeAt(_36c)===35&&_357.charCodeAt(_36c+1)===35){
_51c=2;
}
}
_3b4=_51e&&_51e.parameterScope;
_51c--;
}
}
if(!_51e&&(!_51c&&!_3b1||_36c<_358)&&_356.preprocessIsMacro(word)){
_3b4=null;
_51e=_356.preprocessGetMacro(word);
if(_51e){
if(!_3b0||!_3b0.macro.isArgument){
var i=_3af.length,_523;
while(i>0){
var item=_3af[--i],_524=item.macro;
if(_524.identifier===word&&!(_523&&_523.isArgument)){
_51e=null;
}
_523=_524;
}
}
}else{
_51e=_375(word);
}
}
if(_51e){
var _525=_38a;
var _526;
var _527=_51e.parameters;
var _528;
if(_527){
var pos=_36c;
var loc;
if(_356.locations){
loc=new _443();
}
if(_468(true,true)===true&&_522(40)||_357.charCodeAt(_36c)===40){
_528=true;
}else{
_3b6=loc;
return pos;
}
}
if(!_527||_528){
var _529=_51e.macro;
if(_528){
var _52a=_51e.variadicName;
var _52b=true;
var _52c=0;
_526=Object.create(null);
_468(true);
if(_357.charCodeAt(_36c++)!==40){
_37b(_36c-1,"Expected '(' before macro prarameters");
}
_468(true,true,true);
var code=_357.charCodeAt(_36c++);
while(_36c<_358&&code!==41){
if(_52b){
_52b=false;
}else{
if(code===44){
_468(true,true,true);
code=_357.charCodeAt(_36c++);
}else{
_37b(_36c-1,"Expected ',' between macro parameters");
}
}
var _52d=_527[_52c++];
var _52e=_52a&&_527.length===_52c;
var _52f=_36c-1,_530=0;
var _531=_356.locations&&new _448(_36d,_384);
while(_36c<_358&&(_530||code!==41&&(code!==44||_52e))){
if(code===40){
_530++;
}
if(code===41){
_530--;
}
if(code===34||code===39){
var _532=code;
code=_357.charCodeAt(_36c++);
while(_36c<_358&&code!==_532){
if(code===92){
code=_357.charCodeAt(_36c++);
if(code!==_532){
continue;
}
}
code=_357.charCodeAt(_36c++);
}
}
code=_357.charCodeAt(_36c++);
}
var val=_357.slice(_52f,_36c-1);
_526[_52d]=new _36a(_52d,val,null,_52f+_38c,true,_3b5||_3b0,false,_531);
}
if(code!==41){
_37b(_36c,"Expected ')' after macro prarameters");
}
_468(true,true);
}
return _45b(_51e,_38d,_526,_520,_36c,_51b,_51c,_51d);
}
}
};
function _522(_533,_534){
var i=_3af.length;
stackloop:
while(i-->0){
var _535=_3af[i],_536=_535.end,_537=_535.input,_538=_535.inputLen;
for(;;){
var ch=_537.charCodeAt(_536);
if(ch===32){
++_536;
}else{
if(ch===13){
++_536;
var next=_537.charCodeAt(_536);
if(next===10){
++_536;
}
}else{
if(ch===10){
++_536;
}else{
if(ch===9){
++_536;
}else{
if(ch===47){
var next=_537.charCodeAt(_536+1);
if(next===42){
var end=_537.indexOf("*/",_536+=2);
if(end===-1){
_37b(_536-2,"Unterminated comment");
}
_536=end+2;
}else{
if(next===47){
ch=_537.charCodeAt(_536+=2);
while(_536<_358&&ch!==10&&ch!==13&&ch!==8232&&ch!==8233){
++_536;
ch=_537.charCodeAt(_536);
}
}else{
break stackloop;
}
}
}else{
if(ch===160||ch===11||ch===12||ch>=5760&&_43a.test(String.fromCharCode(ch))){
++_536;
}else{
if(_536>=_538){
continue stackloop;
}else{
if(ch===92){
var pos=_536+1;
ch=_537.charCodeAt(pos);
while(pos<_538&&(ch===32||ch===9||ch===11||ch===12||ch>=5760&&_43b.test(String.fromCharCode(ch)))){
ch=_537.charCodeAt(++pos);
}
_37f.lastIndex=0;
var _539=_37f.exec(_537.slice(pos,pos+2));
if(_539&&_539.index===0){
_536=pos+_539[0].length;
}else{
break stackloop;
}
}else{
break stackloop;
}
}
}
}
}
}
}
}
}
}
return _537&&_537.charCodeAt(_536)===_533&&(_534==null||_537.charCodeAt(_536+1)===_534);
};
function _45b(_53a,_53b,_53c,_53d,end,_53e,_53f,_540){
var _541=_53a.macro;
if(!_541&&_53e===_4ce){
_541="1";
}
if(_541){
_49d(_53a,_541,_53b,_53c,_53d,end,_53f);
}else{
if(_3b8){
(_53e===next?_44e:_49c)(_3c1,"");
return true;
}
}
_468();
_53e(true,_53f,_540,true);
return true;
};
function _49d(_542,_543,_544,_545,_546,end,_547,_548){
_3b0={macro:_542,macroOffset:_544,parameterDict:_545,end:end,lastEnd:_38f,inputLen:_358,tokStart:_38a,onlyTransformArgumentsForLastToken:_3b1,currentLine:_36d,currentLineStart:_384,sourceFile:_359};
if(_546){
_3b0.parameterScope=_546;
}
if(_548){
_3b0.isIncludeFile=_548;
}
_3b0.input=_357;
_3af.push(_3b0);
_3b1=_547;
_357=_543;
_358=_543.length;
_38d=_542.start;
_36c=0;
_36d=0;
_384=0;
_389=0;
_38f=0;
if(_542.sourceFile){
_359=_542.sourceFile;
}
};
var _36a=_355.Macro=function _36a(_549,_54a,_54b,_54c,_54d,_54e,_54f,_550,_551){
this.identifier=_549;
if(_54a!=null){
this.macro=_54a;
}
if(_54b){
this.parameters=_54b;
}
if(_54c!=null){
this.start=_54c;
}
if(_54d){
this.isArgument=true;
}
if(_54e){
this.parameterScope=_54e;
}
if(_54f){
this.variadicName=_54f;
}
if(_550){
this.locationOffset=_550;
}
if(_551){
this.sourceFile=_551;
}
};
_36a.prototype.isParameterFunction=function(){
return this.isParameterFunctionVar||(this.isParameterFunctionVar=_374((this.parameters||[]).join(" ")));
};
function next(_552,_553,_554){
if(!_552){
_3a1=_38a;
_3a2=_38b;
_3a0=_39e;
_391=_390;
_3a3=_393;
_38e=_38c;
}
_38f=_389;
_390=_3a4=null;
return _457(_554,_553,_552);
};
function _555(_556){
_3a7=_556;
_36c=_3a2;
while(_36c<_384){
_384=_357.lastIndexOf("\n",_384-2)+1;
--_36d;
}
_387();
_457();
};
function _557(){
this.type=null;
this.start=_38a+_38c;
this.end=null;
};
function _558(){
this.start=_392;
this.end=null;
if(_359!=null){
this.source=_359;
}
};
function _4e9(){
var node=new _557();
if(_356.trackComments&&_396){
node.commentsBefore=_396;
_396=null;
}
if(_356.trackSpaces&&_399){
node.spacesBefore=_399;
_399=null;
}
if(_356.locations){
node.loc=new _558();
}
if(_356.ranges){
node.range=[_38a,0];
}
return node;
};
function _4f2(_559){
var node=new _557();
node.start=_559.start;
if(_559.commentsBefore){
node.commentsBefore=_559.commentsBefore;
delete _559.commentsBefore;
}
if(_559.spacesBefore){
node.spacesBefore=_559.spacesBefore;
delete _559.spacesBefore;
}
if(_356.locations){
node.loc=new _558();
node.loc.start=_559.loc.start;
}
if(_356.ranges){
node.range=[_559.range[0],0];
}
return node;
};
var _55a;
function _55b(node,type){
var _55c=_3a2+_38e;
node.type=type;
node.end=_55c;
if(_356.trackComments){
if(_398){
node.commentsAfter=_398;
_398=null;
}else{
if(_55a&&_55a.end===_3a2&&_55a.commentsAfter){
node.commentsAfter=_55a.commentsAfter;
delete _55a.commentsAfter;
}
}
if(!_356.trackSpaces){
_55a=node;
}
}
if(_356.trackSpaces){
if(_39b){
node.spacesAfter=_39b;
_39b=null;
}else{
if(_55a&&_55a.end===_3a2&&_55a.spacesAfter){
node.spacesAfter=_55a.spacesAfter;
delete _55a.spacesAfter;
}
}
_55a=node;
}
if(_356.locations){
node.loc.end=_3a3;
}
if(_356.ranges){
node.range[1]=_55c;
}
return node;
};
function _55d(stmt){
return _356.ecmaVersion>=5&&stmt.type==="ExpressionStatement"&&stmt.expression.type==="Literal"&&stmt.expression.value==="use strict";
};
function eat(type){
if(_394===type){
next();
return true;
}
};
function _55e(){
return !_356.strictSemicolons&&(_394===_3c2||_394===_417||_440.test(_3a0.slice(_3a2,_391||_388))||_3a4&&_356.objj||_391!=null);
};
function _55f(){
if(!eat(_41b)&&!_55e()){
_37b(_38a,"Expected a semicolon");
}
};
function _560(type,_561){
if(_394===type){
next();
}else{
_561?_37b(_38a,_561):_4f9();
}
};
function _4f9(){
_37b(_38a,"Unexpected token");
};
function _562(expr){
if(expr.type!=="Identifier"&&expr.type!=="MemberExpression"&&expr.type!=="Dereference"){
_37b(expr.start,"Assigning to rvalue");
}
if(_3a7&&expr.type==="Identifier"&&_436(expr.name)){
_37b(expr.start,"Assigning to "+expr.name+" in strict mode");
}
};
function _35e(_563){
_3a1=_38f=_3a2=0;
if(_356.preprocess){
var _564=_356.preIncludeFiles;
if(_564&&_564.length){
for(var i=_564.length-1;i>=0;i--){
var _565=_564[i];
var _566=new _36a(null,_565.include,null,0,false,null,false,null,_565.sourceFile);
_49d(_566,_566.macro,0,null,null,_36c,null,true);
_387();
}
}
}
if(_356.locations){
_3a3=new _443();
}
_3a5=_3a7=null;
_3a6=[];
_457();
var node=_563||_4e9(),_567=true;
if(!_563){
node.body=[];
}
while(_394!==_3c2){
var stmt=_568();
node.body.push(stmt);
if(_567&&_55d(stmt)){
_555(true);
}
_567=false;
}
return _55b(node,"Program");
};
var _569={kind:"loop"},_56a={kind:"switch"};
function _568(){
if(_394===_422||_394===_424&&_395=="/="){
_457(true);
}
var _56b=_394,node=_4e9();
if(_3a4){
node.expression=_56c(_3a4,_3a4.object);
_55f();
return _55b(node,"ExpressionStatement");
}
switch(_56b){
case _3c4:
case _3c7:
next();
var _56d=_56b===_3c4;
if(eat(_41b)||_55e()){
node.label=null;
}else{
if(_394!==_3c1){
_4f9();
}else{
node.label=_56e();
_55f();
}
}
for(var i=0;i<_3a6.length;++i){
var lab=_3a6[i];
if(node.label==null||lab.name===node.label.name){
if(lab.kind!=null&&(_56d||lab.kind==="loop")){
break;
}
if(node.label&&_56d){
break;
}
}
}
if(i===_3a6.length){
_37b(node.start,"Unsyntactic "+_56b.keyword);
}
return _55b(node,_56d?"BreakStatement":"ContinueStatement");
case _3c8:
next();
_55f();
return _55b(node,"DebuggerStatement");
case _3ca:
next();
_3a6.push(_569);
node.body=_568();
_3a6.pop();
_560(_3d5,"Expected 'while' at end of do statement");
node.test=_56f();
_55f();
return _55b(node,"DoWhileStatement");
case _3cd:
next();
_3a6.push(_569);
_560(_418,"Expected '(' after 'for'");
if(_394===_41b){
return _570(node,null);
}
if(_394===_3d4){
var init=_4e9();
next();
_571(init,true);
if(init.declarations.length===1&&eat(_3dd)){
return _572(node,init);
}
return _570(node,init);
}
var init=_573(false,true);
if(eat(_3dd)){
_562(init);
return _572(node,init);
}
return _570(node,init);
case _3ce:
next();
return _574(node,true);
case _3cf:
next();
node.test=_56f();
node.consequent=_568();
node.alternate=eat(_3cb)?_568():null;
return _55b(node,"IfStatement");
case _3d0:
if(!_3a5){
_37b(_38a,"'return' outside of function");
}
next();
if(eat(_41b)||_55e()){
node.argument=null;
}else{
node.argument=_573();
_55f();
}
return _55b(node,"ReturnStatement");
case _3d1:
next();
node.discriminant=_56f();
node.cases=[];
_560(_416,"Expected '{' in switch statement");
_3a6.push(_56a);
for(var cur,_575;_394!=_417;){
if(_394===_3c5||_394===_3c9){
var _576=_394===_3c5;
if(cur){
_55b(cur,"SwitchCase");
}
node.cases.push(cur=_4e9());
cur.consequent=[];
next();
if(_576){
cur.test=_573();
}else{
if(_575){
_37b(_3a1,"Multiple default clauses");
}
_575=true;
cur.test=null;
}
_560(_41c,"Expected ':' after case clause");
}else{
if(!cur){
_4f9();
}
cur.consequent.push(_568());
}
}
if(cur){
_55b(cur,"SwitchCase");
}
next();
_3a6.pop();
return _55b(node,"SwitchStatement");
case _3d2:
next();
if(_440.test(_39e.slice(_3a2,_38a))){
_37b(_3a2,"Illegal newline after throw");
}
node.argument=_573();
_55f();
return _55b(node,"ThrowStatement");
case _3d3:
next();
node.block=_577();
node.handler=null;
if(_394===_3c6){
var _578=_4e9();
next();
_560(_418,"Expected '(' after 'catch'");
_578.param=_56e();
if(_3a7&&_436(_578.param.name)){
_37b(_578.param.start,"Binding "+_578.param.name+" in strict mode");
}
_560(_419,"Expected closing ')' after catch");
_578.guard=null;
_578.body=_577();
node.handler=_55b(_578,"CatchClause");
}
node.guardedHandlers=_3bd;
node.finalizer=eat(_3cc)?_577():null;
if(!node.handler&&!node.finalizer){
_37b(node.start,"Missing catch or finally clause");
}
return _55b(node,"TryStatement");
case _3d4:
next();
node=_571(node);
_55f();
return node;
case _3d5:
next();
node.test=_56f();
_3a6.push(_569);
node.body=_568();
_3a6.pop();
return _55b(node,"WhileStatement");
case _3d6:
if(_3a7){
_37b(_38a,"'with' in strict mode");
}
next();
node.object=_56f();
node.body=_568();
return _55b(node,"WithStatement");
case _416:
return _577();
case _41b:
next();
return _55b(node,"EmptyStatement");
case _3ee:
if(_356.objj){
next();
node.classname=_56e(true);
if(eat(_41c)){
node.superclassname=_56e(true);
}else{
if(eat(_418)){
node.categoryname=_56e(true);
_560(_419,"Expected closing ')' after category name");
}
}
if(_395==="<"){
next();
var _579=[],_57a=true;
node.protocols=_579;
while(_395!==">"){
if(!_57a){
_560(_41a,"Expected ',' between protocol names");
}else{
_57a=false;
}
_579.push(_56e(true));
}
next();
}
if(eat(_416)){
node.ivardeclarations=[];
for(;;){
if(eat(_417)){
break;
}
_57b(node);
}
node.endOfIvars=_38a;
}
node.body=[];
while(!eat(_3e1)){
if(_394===_3c2){
_37b(_36c,"Expected '@end' after '@interface'");
}
node.body.push(_57c());
}
return _55b(node,"InterfaceDeclarationStatement");
}
break;
case _3de:
if(_356.objj){
next();
node.classname=_56e(true);
if(eat(_41c)){
node.superclassname=_56e(true);
}else{
if(eat(_418)){
node.categoryname=_56e(true);
_560(_419,"Expected closing ')' after category name");
}
}
if(_395==="<"){
next();
var _579=[],_57a=true;
node.protocols=_579;
while(_395!==">"){
if(!_57a){
_560(_41a,"Expected ',' between protocol names");
}else{
_57a=false;
}
_579.push(_56e(true));
}
next();
}
if(eat(_416)){
node.ivardeclarations=[];
for(;;){
if(eat(_417)){
break;
}
_57b(node);
}
node.endOfIvars=_38a;
}
node.body=[];
while(!eat(_3e1)){
if(_394===_3c2){
_37b(_36c,"Expected '@end' after '@implementation'");
}
node.body.push(_57c());
}
return _55b(node,"ClassDeclarationStatement");
}
break;
case _3eb:
if(_356.objj&&_357.charCodeAt(_36c)!==40){
next();
node.protocolname=_56e(true);
if(_395==="<"){
next();
var _579=[],_57a=true;
node.protocols=_579;
while(_395!==">"){
if(!_57a){
_560(_41a,"Expected ',' between protocol names");
}else{
_57a=false;
}
_579.push(_56e(true));
}
next();
}
while(!eat(_3e1)){
if(_394===_3c2){
_37b(_36c,"Expected '@end' after '@protocol'");
}
if(eat(_3ed)){
continue;
}
if(eat(_3ec)){
while(!eat(_3ed)&&_394!==_3e1){
(node.optional||(node.optional=[])).push(_57d());
}
}else{
(node.required||(node.required=[])).push(_57d());
}
}
return _55b(node,"ProtocolDeclarationStatement");
}
break;
case _3e2:
if(_356.objj){
next();
if(_394===_3c0){
node.localfilepath=true;
}else{
if(_394===_3f0){
node.localfilepath=false;
}else{
_4f9();
}
}
node.filename=_57e();
return _55b(node,"ImportStatement");
}
break;
case _3fd:
if(_356.objj){
next();
return _55b(node,"PreprocessStatement");
}
break;
case _3e5:
if(_356.objj){
next();
node.id=_56e(false);
return _55b(node,"ClassStatement");
}
break;
case _3e6:
if(_356.objj){
next();
node.id=_56e(false);
return _55b(node,"GlobalStatement");
}
break;
case _3ef:
if(_356.objj){
next();
node.typedefname=_56e(true);
return _55b(node,"TypeDefStatement");
}
break;
}
var _57f=_395,expr=_573();
if(_56b===_3c1&&expr.type==="Identifier"&&eat(_41c)){
for(var i=0;i<_3a6.length;++i){
if(_3a6[i].name===_57f){
_37b(expr.start,"Label '"+_57f+"' is already declared");
}
}
var kind=_394.isLoop?"loop":_394===_3d1?"switch":null;
_3a6.push({name:_57f,kind:kind});
node.body=_568();
_3a6.pop();
node.label=expr;
return _55b(node,"LabeledStatement");
}else{
node.expression=expr;
_55f();
return _55b(node,"ExpressionStatement");
}
};
function _57b(node){
var _580;
if(eat(_3df)){
_580=true;
}
var type=_581();
if(_3a7&&_436(type.name)){
_37b(type.start,"Binding "+type.name+" in strict mode");
}
for(;;){
var decl=_4e9();
if(_580){
decl.outlet=_580;
}
decl.ivartype=type;
decl.id=_56e();
if(_3a7&&_436(decl.id.name)){
_37b(decl.id.start,"Binding "+decl.id.name+" in strict mode");
}
if(eat(_3e0)){
decl.accessors={};
if(eat(_418)){
if(!eat(_419)){
for(;;){
var _582=_56e(true);
switch(_582.name){
case "property":
case "getter":
_560(_423,"Expected '=' after 'getter' accessor attribute");
decl.accessors[_582.name]=_56e(true);
break;
case "setter":
_560(_423,"Expected '=' after 'setter' accessor attribute");
var _583=_56e(true);
decl.accessors[_582.name]=_583;
if(eat(_41c)){
_583.end=_38a;
}
_583.name+=":";
break;
case "readwrite":
case "readonly":
case "copy":
decl.accessors[_582.name]=true;
break;
default:
_37b(_582.start,"Unknown accessors attribute '"+_582.name+"'");
}
if(!eat(_41a)){
break;
}
}
_560(_419,"Expected closing ')' after accessor attributes");
}
}
}
_55b(decl,"IvarDeclaration");
node.ivardeclarations.push(decl);
if(!eat(_41a)){
break;
}
}
_55f();
};
function _584(node){
node.methodtype=_395;
_560(_425,"Method declaration must start with '+' or '-'");
if(eat(_418)){
var _585=_4e9();
if(eat(_3e3)){
node.action=_55b(_585,"ObjectiveJActionType");
_585=_4e9();
}
if(!eat(_419)){
node.returntype=_581(_585);
_560(_419,"Expected closing ')' after method return type");
}
}
var _586=true,_587=[],args=[];
node.selectors=_587;
node.arguments=args;
for(;;){
if(_394!==_41c){
_587.push(_56e(true));
if(_586&&_394!==_41c){
break;
}
}else{
_587.push(null);
}
_560(_41c,"Expected ':' in selector");
var _588={};
args.push(_588);
if(eat(_418)){
_588.type=_581();
_560(_419,"Expected closing ')' after method argument type");
}
_588.identifier=_56e(false);
if(_394===_416||_394===_41b){
break;
}
if(eat(_41a)){
_560(_420,"Expected '...' after ',' in method declaration");
node.parameters=true;
break;
}
_586=false;
}
};
function _57c(){
var _589=_4e9();
if(_395==="+"||_395==="-"){
_584(_589);
eat(_41b);
_589.startOfBody=_3a2;
var _58a=_3a5,_58b=_3a6;
_3a5=true;
_3a6=[];
_589.body=_577(true);
_3a5=_58a;
_3a6=_58b;
return _55b(_589,"MethodDeclarationStatement");
}else{
return _568();
}
};
function _57d(){
var _58c=_4e9();
_584(_58c);
_55f();
return _55b(_58c,"MethodDeclarationStatement");
};
function _56f(){
_560(_418,"Expected '(' before expression");
var val=_573();
_560(_419,"Expected closing ')' after expression");
return val;
};
function _577(_58d){
var node=_4e9(),_58e=true,_3a7=false,_58f;
node.body=[];
_560(_416,"Expected '{' before block");
while(!eat(_417)){
var stmt=_568();
node.body.push(stmt);
if(_58e&&_58d&&_55d(stmt)){
_58f=_3a7;
_555(_3a7=true);
}
_58e=false;
}
if(_3a7&&!_58f){
_555(false);
}
return _55b(node,"BlockStatement");
};
function _570(node,init){
node.init=init;
_560(_41b,"Expected ';' in for statement");
node.test=_394===_41b?null:_573();
_560(_41b,"Expected ';' in for statement");
node.update=_394===_419?null:_573();
_560(_419,"Expected closing ')' in for statement");
node.body=_568();
_3a6.pop();
return _55b(node,"ForStatement");
};
function _572(node,init){
node.left=init;
node.right=_573();
_560(_419,"Expected closing ')' in for statement");
node.body=_568();
_3a6.pop();
return _55b(node,"ForInStatement");
};
function _571(node,noIn){
node.declarations=[];
node.kind="var";
for(;;){
var decl=_4e9();
decl.id=_56e();
if(_3a7&&_436(decl.id.name)){
_37b(decl.id.start,"Binding "+decl.id.name+" in strict mode");
}
decl.init=eat(_423)?_573(true,noIn):null;
node.declarations.push(_55b(decl,"VariableDeclarator"));
if(!eat(_41a)){
break;
}
}
return _55b(node,"VariableDeclaration");
};
function _573(_590,noIn){
var expr=_591(noIn);
if(!_590&&_394===_41a){
var node=_4f2(expr);
node.expressions=[expr];
while(eat(_41a)){
node.expressions.push(_591(noIn));
}
return _55b(node,"SequenceExpression");
}
return expr;
};
function _591(noIn){
var left=_592(noIn);
if(_394.isAssign){
var node=_4f2(left);
node.operator=_395;
node.left=left;
next();
node.right=_591(noIn);
_562(left);
return _55b(node,"AssignmentExpression");
}
return left;
};
function _592(noIn){
var expr=_593(noIn);
if(eat(_41e)){
var node=_4f2(expr);
node.test=expr;
node.consequent=_573(true);
_560(_41c,"Expected ':' in conditional expression");
node.alternate=_573(true,noIn);
return _55b(node,"ConditionalExpression");
}
return expr;
};
function _593(noIn){
return _594(_595(),-1,noIn);
};
function _594(left,_596,noIn){
var prec=_394.binop;
if(prec!=null&&(!noIn||_394!==_3dd)){
if(prec>_596){
var node=_4f2(left);
node.left=left;
node.operator=_395;
next();
node.right=_594(_595(),prec,noIn);
var node=_55b(node,/&&|\|\|/.test(node.operator)?"LogicalExpression":"BinaryExpression");
return _594(node,_596,noIn);
}
}
return left;
};
function _595(){
if(_394.prefix){
var node=_4e9(),_597=_394.isUpdate;
node.operator=_395;
node.prefix=true;
_386=true;
next();
node.argument=_595();
if(_597){
_562(node.argument);
}else{
if(_3a7&&node.operator==="delete"&&node.argument.type==="Identifier"){
_37b(node.start,"Deleting local variable in strict mode");
}
}
return _55b(node,_597?"UpdateExpression":"UnaryExpression");
}
var expr=_598();
while(_394.postfix&&!_55e()){
var node=_4f2(expr);
node.operator=_395;
node.prefix=false;
node.argument=expr;
_562(expr);
next();
expr=_55b(node,"UpdateExpression");
}
return expr;
};
function _598(){
return _599(_59a());
};
function _599(base,_59b){
if(eat(_41d)){
var node=_4f2(base);
node.object=base;
node.property=_56e(true);
node.computed=false;
return _599(_55b(node,"MemberExpression"),_59b);
}else{
if(_356.objj){
var _59c=_4e9();
}
if(eat(_414)){
var expr=_573();
if(_356.objj&&_394!==_415){
_59c.object=expr;
_3a4=_59c;
return base;
}
var node=_4f2(base);
node.object=base;
node.property=expr;
node.computed=true;
_560(_415,"Expected closing ']' in subscript");
return _599(_55b(node,"MemberExpression"),_59b);
}else{
if(!_59b&&eat(_418)){
var node=_4f2(base);
node.callee=base;
node.arguments=_59d(_419,_394===_419?null:_573(true),false);
return _599(_55b(node,"CallExpression"),_59b);
}
}
}
return base;
};
function _59a(){
switch(_394){
case _3d8:
var node=_4e9();
next();
return _55b(node,"ThisExpression");
case _3c1:
return _56e();
case _3be:
case _3c0:
case _3bf:
return _57e();
case _3da:
case _3db:
case _3dc:
var node=_4e9();
node.value=_394.atomValue;
node.raw=_394.keyword;
next();
return _55b(node,"Literal");
case _418:
var _59e=_392,_59f=_38c,_5a0=_38a+_59f;
next();
var val=_573();
val.start=_5a0;
val.end=_38b+_59f;
if(_356.locations){
val.loc.start=_59e;
val.loc.end=_393;
}
if(_356.ranges){
val.range=[_5a0,_38b+_38e];
}
_560(_419,"Expected closing ')' in expression");
return val;
case _3e8:
var node=_4e9(),_5a1=null;
next();
_560(_414,"Expected '[' at beginning of array literal");
if(_394!==_415){
_5a1=_573(true,true);
}
node.elements=_59d(_415,_5a1,true,true);
return _55b(node,"ArrayLiteral");
case _414:
var node=_4e9(),_5a1=null;
next();
if(_394!==_41a&&_394!==_415){
_5a1=_573(true,true);
if(_394!==_41a&&_394!==_415){
return _56c(node,_5a1);
}
}
node.elements=_59d(_415,_5a1,true,true);
return _55b(node,"ArrayExpression");
case _3e7:
var node=_4e9();
next();
var r=_5a2();
node.keys=r[0];
node.values=r[1];
return _55b(node,"DictionaryLiteral");
case _416:
return _5a3();
case _3ce:
var node=_4e9();
next();
return _574(node,false);
case _3d7:
return _5a4();
case _3e4:
var node=_4e9();
next();
_560(_418,"Expected '(' after '@selector'");
_5a5(node,_419);
_560(_419,"Expected closing ')' after selector");
return _55b(node,"SelectorLiteralExpression");
case _3eb:
var node=_4e9();
next();
_560(_418,"Expected '(' after '@protocol'");
node.id=_56e(true);
_560(_419,"Expected closing ')' after protocol name");
return _55b(node,"ProtocolLiteralExpression");
case _3e9:
var node=_4e9();
next();
_560(_418,"Expected '(' after '@ref'");
node.element=_56e(node,_419);
_560(_419,"Expected closing ')' after ref");
return _55b(node,"Reference");
case _3ea:
var node=_4e9();
next();
_560(_418,"Expected '(' after '@deref'");
node.expr=_573(true,true);
_560(_419,"Expected closing ')' after deref");
return _55b(node,"Dereference");
default:
if(_394.okAsIdent){
return _56e();
}
_4f9();
}
};
function _56c(node,_5a6){
_5a7(node,_415);
if(_5a6.type==="Identifier"&&_5a6.name==="super"){
node.superObject=true;
}else{
node.object=_5a6;
}
return _55b(node,"MessageSendExpression");
};
function _5a5(node,_5a8){
var _5a9=true,_5aa=[];
for(;;){
if(_394!==_41c){
_5aa.push((_56e(true)).name);
if(_5a9&&_394===_5a8){
break;
}
}
_560(_41c,"Expected ':' in selector");
_5aa.push(":");
if(_394===_5a8){
break;
}
_5a9=false;
}
node.selector=_5aa.join("");
};
function _5a7(node,_5ab){
var _5ac=true,_5ad=[],args=[],_5ae=[];
node.selectors=_5ad;
node.arguments=args;
for(;;){
if(_394!==_41c){
_5ad.push(_56e(true));
if(_5ac&&eat(_5ab)){
break;
}
}else{
_5ad.push(null);
}
_560(_41c,"Expected ':' in selector");
args.push(_573(true,true));
if(eat(_5ab)){
break;
}
if(_394===_41a){
node.parameters=[];
while(eat(_41a)){
node.parameters.push(_573(true,true));
}
eat(_5ab);
break;
}
_5ac=false;
}
};
function _5a4(){
var node=_4e9();
next();
node.callee=_599(_59a(false),true);
if(eat(_418)){
node.arguments=_59d(_419,_394===_419?null:_573(true),false);
}else{
node.arguments=_3bd;
}
return _55b(node,"NewExpression");
};
function _5a3(){
var node=_4e9(),_5af=true,_5b0=false;
node.properties=[];
next();
while(!eat(_417)){
if(!_5af){
_560(_41a,"Expected ',' in object literal");
if(_356.allowTrailingCommas&&eat(_417)){
break;
}
}else{
_5af=false;
}
var prop={key:_5b1()},_5b2=false,kind;
if(eat(_41c)){
prop.value=_573(true);
kind=prop.kind="init";
}else{
if(_356.ecmaVersion>=5&&prop.key.type==="Identifier"&&(prop.key.name==="get"||prop.key.name==="set")){
_5b2=_5b0=true;
kind=prop.kind=prop.key.name;
prop.key=_5b1();
if(_394!==_418){
_4f9();
}
prop.value=_574(_4e9(),false);
}else{
_4f9();
}
}
if(prop.key.type==="Identifier"&&(_3a7||_5b0)){
for(var i=0;i<node.properties.length;++i){
var _5b3=node.properties[i];
if(_5b3.key.name===prop.key.name){
var _5b4=kind==_5b3.kind||_5b2&&_5b3.kind==="init"||kind==="init"&&(_5b3.kind==="get"||_5b3.kind==="set");
if(_5b4&&!_3a7&&kind==="init"&&_5b3.kind==="init"){
_5b4=false;
}
if(_5b4){
_37b(prop.key.start,"Redefinition of property");
}
}
}
}
node.properties.push(prop);
}
return _55b(node,"ObjectExpression");
};
function _5b1(){
if(_394===_3be||_394===_3c0){
return _59a();
}
return _56e(true);
};
function _574(node,_5b5){
if(_394===_3c1){
node.id=_56e();
}else{
if(_5b5){
_4f9();
}else{
node.id=null;
}
}
node.params=[];
var _5b6=true;
_560(_418,"Expected '(' before function parameters");
while(!eat(_419)){
if(!_5b6){
_560(_41a,"Expected ',' between function parameters");
}else{
_5b6=false;
}
node.params.push(_56e());
}
var _5b7=_3a5,_5b8=_3a6;
_3a5=true;
_3a6=[];
node.body=_577(true);
_3a5=_5b7;
_3a6=_5b8;
if(_3a7||node.body.body.length&&_55d(node.body.body[0])){
for(var i=node.id?-1:0;i<node.params.length;++i){
var id=i<0?node.id:node.params[i];
if(_435(id.name)||_436(id.name)){
_37b(id.start,"Defining '"+id.name+"' in strict mode");
}
if(i>=0){
for(var j=0;j<i;++j){
if(id.name===node.params[j].name){
_37b(id.start,"Argument name clash in strict mode");
}
}
}
}
}
return _55b(node,_5b5?"FunctionDeclaration":"FunctionExpression");
};
function _59d(_5b9,_5ba,_5bb,_5bc){
if(_5ba&&eat(_5b9)){
return [_5ba];
}
var elts=[],_5bd=true;
while(!eat(_5b9)){
if(_5bd){
_5bd=false;
if(_5bc&&_394===_41a&&!_5ba){
elts.push(null);
}else{
elts.push(_5ba);
}
}else{
_560(_41a,"Expected ',' between expressions");
if(_5bb&&_356.allowTrailingCommas&&eat(_5b9)){
break;
}
if(_5bc&&_394===_41a){
elts.push(null);
}else{
elts.push(_573(true));
}
}
}
return elts;
};
function _5a2(){
_560(_416,"Expected '{' before dictionary");
var keys=[],_5be=[],_5bf=true;
while(!eat(_417)){
if(!_5bf){
_560(_41a,"Expected ',' between expressions");
if(_356.allowTrailingCommas&&eat(_417)){
break;
}
}
keys.push(_573(true,true));
_560(_41c,"Expected ':' between dictionary key and value");
_5be.push(_573(true,true));
_5bf=false;
}
return [keys,_5be];
};
function _56e(_5c0){
var node=_4e9();
node.name=_394===_3c1?_395:(_5c0&&!_356.forbidReserved||_394.okAsIdent)&&_394.keyword||_4f9();
_386=false;
next();
return _55b(node,"Identifier");
};
function _57e(){
var node=_4e9();
node.value=_395;
node.raw=_39e.slice(_38a,_38b);
next();
return _55b(node,"Literal");
};
function _581(_5c1){
var node=_5c1?_4f2(_5c1):_4e9(),_5c2=false;
if(_394===_3c1){
node.name=_395;
node.typeisclass=true;
_5c2=true;
next();
}else{
node.typeisclass=false;
node.name=_394.keyword;
if(!eat(_3d9)){
if(eat(_3f8)){
_5c2=true;
}else{
var _5c3;
if(eat(_3fb)||eat(_3f9)||eat(_3fa)||eat(_3fc)){
_5c3=_394.keyword;
}else{
if(eat(_3f2)||eat(_3f1)){
_5c3=_394.keyword||true;
}
if(eat(_3f4)||eat(_3f3)||eat(_3f5)){
if(_5c3){
node.name+=" "+_5c3;
}
_5c3=_394.keyword||true;
}else{
if(eat(_3f6)){
if(_5c3){
node.name+=" "+_5c3;
}
_5c3=_394.keyword||true;
}
if(eat(_3f7)){
if(_5c3){
node.name+=" "+_5c3;
}
_5c3=_394.keyword||true;
if(eat(_3f7)){
node.name+=" "+_5c3;
}
}
}
if(!_5c3){
node.name=!_356.forbidReserved&&_394.keyword||_4f9();
node.typeisclass=true;
_5c2=true;
next();
}
}
}
}
}
if(_5c2){
if(_395==="<"){
var _5c4=true,_5c5=[];
node.protocols=_5c5;
do{
next();
if(_5c4){
_5c4=false;
}else{
eat(_41a);
}
_5c5.push(_56e(true));
}while(_395!==">");
next();
}
}
return _55b(node,"ObjectiveJType");
};
})(_2.acorn||(_2.acorn={}),_2.acorn.walk||(_2.acorn.walk=typeof acorn!=="undefined"&&acorn.walk)||(_2.acorn.walk={}));
if(!_2.acorn){
_2.acorn={};
_2.acorn.walk={};
}
(function(_5c6){
"use strict";
_5c6.simple=function(node,_5c7,base,_5c8){
if(!base){
base=_5c6;
}
function c(node,st,_5c9){
var type=_5c9||node.type,_5ca=_5c7[type];
if(_5ca){
_5ca(node,st);
}
base[type](node,st,c);
};
c(node,_5c8);
};
_5c6.recursive=function(node,_5cb,_5cc,base){
var _5cd=_5c6.make(_5cc,base);
function c(node,st,_5ce){
return _5cd[_5ce||node.type](node,st,c);
};
return c(node,_5cb);
};
_5c6.make=function(_5cf,base){
if(!base){
base=_5c6;
}
var _5d0={};
for(var type in base){
_5d0[type]=base[type];
}
for(var type in _5cf){
_5d0[type]=_5cf[type];
}
return _5d0;
};
function _5d1(node,st,c){
c(node,st);
};
function _5d2(node,st,c){
};
_5c6.Program=_5c6.BlockStatement=function(node,st,c){
for(var i=0;i<node.body.length;++i){
c(node.body[i],st,"Statement");
}
};
_5c6.Statement=_5d1;
_5c6.EmptyStatement=_5d2;
_5c6.ExpressionStatement=function(node,st,c){
c(node.expression,st,"Expression");
};
_5c6.IfStatement=function(node,st,c){
c(node.test,st,"Expression");
c(node.consequent,st,"Statement");
if(node.alternate){
c(node.alternate,st,"Statement");
}
};
_5c6.LabeledStatement=function(node,st,c){
c(node.body,st,"Statement");
};
_5c6.BreakStatement=_5c6.ContinueStatement=_5d2;
_5c6.WithStatement=function(node,st,c){
c(node.object,st,"Expression");
c(node.body,st,"Statement");
};
_5c6.SwitchStatement=function(node,st,c){
c(node.discriminant,st,"Expression");
for(var i=0;i<node.cases.length;++i){
var cs=node.cases[i];
if(cs.test){
c(cs.test,st,"Expression");
}
for(var j=0;j<cs.consequent.length;++j){
c(cs.consequent[j],st,"Statement");
}
}
};
_5c6.ReturnStatement=function(node,st,c){
if(node.argument){
c(node.argument,st,"Expression");
}
};
_5c6.ThrowStatement=function(node,st,c){
c(node.argument,st,"Expression");
};
_5c6.TryStatement=function(node,st,c){
c(node.block,st,"Statement");
if(node.handler){
c(node.handler.body,st,"ScopeBody");
}
if(node.finalizer){
c(node.finalizer,st,"Statement");
}
};
_5c6.WhileStatement=function(node,st,c){
c(node.test,st,"Expression");
c(node.body,st,"Statement");
};
_5c6.DoWhileStatement=function(node,st,c){
c(node.body,st,"Statement");
c(node.test,st,"Expression");
};
_5c6.ForStatement=function(node,st,c){
if(node.init){
c(node.init,st,"ForInit");
}
if(node.test){
c(node.test,st,"Expression");
}
if(node.update){
c(node.update,st,"Expression");
}
c(node.body,st,"Statement");
};
_5c6.ForInStatement=function(node,st,c){
c(node.left,st,"ForInit");
c(node.right,st,"Expression");
c(node.body,st,"Statement");
};
_5c6.ForInit=function(node,st,c){
if(node.type=="VariableDeclaration"){
c(node,st);
}else{
c(node,st,"Expression");
}
};
_5c6.DebuggerStatement=_5d2;
_5c6.FunctionDeclaration=function(node,st,c){
c(node,st,"Function");
};
_5c6.VariableDeclaration=function(node,st,c){
for(var i=0;i<node.declarations.length;++i){
var decl=node.declarations[i];
if(decl.init){
c(decl.init,st,"Expression");
}
}
};
_5c6.Function=function(node,st,c){
c(node.body,st,"ScopeBody");
};
_5c6.ScopeBody=function(node,st,c){
c(node,st,"Statement");
};
_5c6.Expression=_5d1;
_5c6.ThisExpression=_5d2;
_5c6.ArrayExpression=_5c6.ArrayLiteral=function(node,st,c){
for(var i=0;i<node.elements.length;++i){
var elt=node.elements[i];
if(elt){
c(elt,st,"Expression");
}
}
};
_5c6.DictionaryLiteral=function(node,st,c){
for(var i=0;i<node.keys.length;i++){
var key=node.keys[i];
c(key,st,"Expression");
var _5d3=node.values[i];
c(_5d3,st,"Expression");
}
};
_5c6.ObjectExpression=function(node,st,c){
for(var i=0;i<node.properties.length;++i){
c(node.properties[i].value,st,"Expression");
}
};
_5c6.FunctionExpression=_5c6.FunctionDeclaration;
_5c6.SequenceExpression=function(node,st,c){
for(var i=0;i<node.expressions.length;++i){
c(node.expressions[i],st,"Expression");
}
};
_5c6.UnaryExpression=_5c6.UpdateExpression=function(node,st,c){
c(node.argument,st,"Expression");
};
_5c6.BinaryExpression=_5c6.AssignmentExpression=_5c6.LogicalExpression=function(node,st,c){
c(node.left,st,"Expression");
c(node.right,st,"Expression");
};
_5c6.ConditionalExpression=function(node,st,c){
c(node.test,st,"Expression");
c(node.consequent,st,"Expression");
c(node.alternate,st,"Expression");
};
_5c6.NewExpression=_5c6.CallExpression=function(node,st,c){
c(node.callee,st,"Expression");
if(node.arguments){
for(var i=0;i<node.arguments.length;++i){
c(node.arguments[i],st,"Expression");
}
}
};
_5c6.MemberExpression=function(node,st,c){
c(node.object,st,"Expression");
if(node.computed){
c(node.property,st,"Expression");
}
};
_5c6.Identifier=_5c6.Literal=_5d2;
_5c6.ClassDeclarationStatement=function(node,st,c){
if(node.ivardeclarations){
for(var i=0;i<node.ivardeclarations.length;++i){
c(node.ivardeclarations[i],st,"IvarDeclaration");
}
}
for(var i=0;i<node.body.length;++i){
c(node.body[i],st,"Statement");
}
};
_5c6.ImportStatement=_5d2;
_5c6.IvarDeclaration=_5d2;
_5c6.PreprocessStatement=_5d2;
_5c6.ClassStatement=_5d2;
_5c6.GlobalStatement=_5d2;
_5c6.ProtocolDeclarationStatement=function(node,st,c){
if(node.required){
for(var i=0;i<node.required.length;++i){
c(node.required[i],st,"Statement");
}
}
if(node.optional){
for(var i=0;i<node.optional.length;++i){
c(node.optional[i],st,"Statement");
}
}
};
_5c6.TypeDefStatement=_5d2;
_5c6.MethodDeclarationStatement=function(node,st,c){
var body=node.body;
if(body){
c(body,st,"Statement");
}
};
_5c6.MessageSendExpression=function(node,st,c){
if(!node.superObject){
c(node.object,st,"Expression");
}
if(node.arguments){
for(var i=0;i<node.arguments.length;++i){
c(node.arguments[i],st,"Expression");
}
}
if(node.parameters){
for(var i=0;i<node.parameters.length;++i){
c(node.parameters[i],st,"Expression");
}
}
};
_5c6.SelectorLiteralExpression=_5d2;
_5c6.ProtocolLiteralExpression=_5d2;
_5c6.Reference=function(node,st,c){
c(node.element,st,"Identifier");
};
_5c6.Dereference=function(node,st,c){
c(node.expr,st,"Expression");
};
function _5d4(prev){
return {vars:Object.create(null),prev:prev};
};
_5c6.scopeVisitor=_5c6.make({Function:function(node,_5d5,c){
var _5d6=_5d4(_5d5);
for(var i=0;i<node.params.length;++i){
_5d6.vars[node.params[i].name]={type:"argument",node:node.params[i]};
}
if(node.id){
var decl=node.type=="FunctionDeclaration";
(decl?_5d5:_5d6).vars[node.id.name]={type:decl?"function":"function name",node:node.id};
}
c(node.body,_5d6,"ScopeBody");
},TryStatement:function(node,_5d7,c){
c(node.block,_5d7,"Statement");
if(node.handler){
var _5d8=_5d4(_5d7);
_5d8.vars[node.handler.param.name]={type:"catch clause",node:node.handler.param};
c(node.handler.body,_5d8,"ScopeBody");
}
if(node.finalizer){
c(node.finalizer,_5d7,"Statement");
}
},VariableDeclaration:function(node,_5d9,c){
for(var i=0;i<node.declarations.length;++i){
var decl=node.declarations[i];
_5d9.vars[decl.id.name]={type:"var",node:decl.id};
if(decl.init){
c(decl.init,_5d9,"Expression");
}
}
}});
})(typeof _2=="undefined"?acorn.walk={}:_2.acorn.walk);
(function(mod){
mod(_2.ObjJCompiler||(_2.ObjJCompiler={}),_2.acorn||acorn,(_2.acorn||acorn).walk,typeof sourceMap!="undefined"?sourceMap:null);
})(function(_5da,_5db,walk,_5dc){
"use strict";
_5da.version="0.3.7";
var _5dd=function(prev,base){
this.vars=Object.create(null);
if(base){
for(var key in base){
this[key]=base[key];
}
}
this.prev=prev;
if(prev){
this.compiler=prev.compiler;
this.nodeStack=prev.nodeStack.slice(0);
this.nodePriorStack=prev.nodePriorStack.slice(0);
this.nodeStackOverrideType=prev.nodeStackOverrideType.slice(0);
}else{
this.nodeStack=[];
this.nodePriorStack=[];
this.nodeStackOverrideType=[];
}
};
_5dd.prototype.toString=function(){
return this.ivars?"ivars: "+JSON.stringify(this.ivars):"<No ivars>";
};
_5dd.prototype.compiler=function(){
return this.compiler;
};
_5dd.prototype.rootScope=function(){
return this.prev?this.prev.rootScope():this;
};
_5dd.prototype.isRootScope=function(){
return !this.prev;
};
_5dd.prototype.currentClassName=function(){
return this.classDef?this.classDef.name:this.prev?this.prev.currentClassName():null;
};
_5dd.prototype.currentProtocolName=function(){
return this.protocolDef?this.protocolDef.name:this.prev?this.prev.currentProtocolName():null;
};
_5dd.prototype.getIvarForCurrentClass=function(_5de){
if(this.ivars){
var ivar=this.ivars[_5de];
if(ivar){
return ivar;
}
}
var prev=this.prev;
if(prev&&!this.classDef){
return prev.getIvarForCurrentClass(_5de);
}
return null;
};
_5dd.prototype.getLvar=function(_5df,_5e0){
if(this.vars){
var lvar=this.vars[_5df];
if(lvar){
return lvar;
}
}
var prev=this.prev;
if(prev&&(!_5e0||!this.methodType)){
return prev.getLvar(_5df,_5e0);
}
return null;
};
_5dd.prototype.currentMethodType=function(){
return this.methodType?this.methodType:this.prev?this.prev.currentMethodType():null;
};
_5dd.prototype.copyAddedSelfToIvarsToParent=function(){
if(this.prev&&this.addedSelfToIvars){
for(var key in this.addedSelfToIvars){
var _5e1=this.addedSelfToIvars[key],_5e2=(this.prev.addedSelfToIvars||(this.prev.addedSelfToIvars=Object.create(null)))[key]||(this.prev.addedSelfToIvars[key]=[]);
_5e2.push.apply(_5e2,_5e1);
}
}
};
_5dd.prototype.addMaybeWarning=function(_5e3){
var _5e4=this.rootScope(),_5e5=_5e4._maybeWarnings;
if(!_5e5){
_5e4._maybeWarnings=_5e5=[_5e3];
}else{
var _5e6=_5e5[_5e5.length-1];
if(!_5e6.isEqualTo(_5e3)){
_5e5.push(_5e3);
}
}
};
_5dd.prototype.maybeWarnings=function(){
return (this.rootScope())._maybeWarnings;
};
_5dd.prototype.pushNode=function(node,_5e7){
var _5e8=this.nodePriorStack,_5e9=_5e8.length,_5ea=_5e9?_5e8[_5e9-1]:null,_5eb=_5e9?this.nodeStack[_5e9-1]:null;
if(_5ea){
if(_5eb!==node){
_5ea.push(node);
}
}
_5e8.push(_5eb===node?_5ea:[]);
this.nodeStack.push(node);
this.nodeStackOverrideType.push(_5e7);
};
_5dd.prototype.popNode=function(){
this.nodeStackOverrideType.pop();
this.nodePriorStack.pop();
return this.nodeStack.pop();
};
_5dd.prototype.currentNode=function(){
var _5ec=this.nodeStack;
return _5ec[_5ec.length-1];
};
_5dd.prototype.currentOverrideType=function(){
var _5ed=this.nodeStackOverrideType;
return _5ed[_5ed.length-1];
};
_5dd.prototype.priorNode=function(){
var _5ee=this.nodePriorStack,_5ef=_5ee.length;
if(_5ef>1){
var _5f0=_5ee[_5ef-2],l=_5f0.length;
return _5f0[l-2]||null;
}
return null;
};
_5dd.prototype.formatDescription=function(_5f1,_5f2,_5f3){
var _5f4=this.nodeStack,_5f5=_5f4.length;
_5f1=_5f1||0;
if(_5f1>=_5f5){
return null;
}
var i=_5f5-_5f1-1;
var _5f6=_5f4[i];
var _5f7=_5f2||this.compiler.formatDescription;
var _5f8=_5f2?_5f2.parent:_5f7;
var _5f9;
if(_5f8){
var _5fa=_5f3===_5f6?this.nodeStackOverrideType[i]:_5f6.type;
_5f9=_5f8[_5fa];
if(_5f3===_5f6&&!_5f9){
return null;
}
}
if(_5f9){
return this.formatDescription(_5f1+1,_5f9);
}else{
_5f9=this.formatDescription(_5f1+1,_5f2,_5f6);
if(_5f9){
return _5f9;
}else{
var _5fb=_5f7.prior;
if(_5fb){
var _5fc=this.priorNode(),_5fd=_5fb[_5fc?_5fc.type:"None"];
if(_5fd){
return _5fd;
}
}
return _5f7;
}
}
};
var _5fe=function(_5ff,node,code){
this.message=_600(_5ff,node,code);
this.node=node;
};
_5fe.prototype.checkIfWarning=function(st){
var _601=this.node.name;
return !st.getLvar(_601)&&typeof _1[_601]==="undefined"&&(typeof window==="undefined"||typeof window[_601]==="undefined")&&!st.compiler.getClassDef(_601);
};
_5fe.prototype.isEqualTo=function(_602){
if(this.message.message!==_602.message.message){
return false;
}
if(this.node.start!==_602.node.start){
return false;
}
if(this.node.end!==_602.node.end){
return false;
}
return true;
};
function _2f7(_603,file,_604){
if(_603){
this.rootNode=new _5dc.SourceNode();
this.concat=this.concatSourceNode;
this.toString=this.toStringSourceNode;
this.isEmpty=this.isEmptySourceNode;
this.appendStringBuffer=this.appendStringBufferSourceNode;
this.length=this.lengthSourceNode;
if(file){
var _605=file.toString(),_606=_605.substr(_605.lastIndexOf("/")+1),_607=_605.substr(0,_605.lastIndexOf("/")+1);
this.filename=_606;
if(_607.length>0){
this.sourceRoot=_607;
}
if(_604!=null){
this.rootNode.setSourceContent(_606,_604);
}
}
if(_604!=null){
this.sourceContent=_604;
}
}else{
this.atoms=[];
this.concat=this.concatString;
this.toString=this.toStringString;
this.isEmpty=this.isEmptyString;
this.appendStringBuffer=this.appendStringBufferString;
this.length=this.lengthString;
}
};
_2f7.prototype.toStringString=function(){
return this.atoms.join("");
};
_2f7.prototype.toStringSourceNode=function(){
return this.rootNode.toStringWithSourceMap({file:this.filename+"s",sourceRoot:this.sourceRoot});
};
_2f7.prototype.concatString=function(_608){
this.atoms.push(_608);
};
_2f7.prototype.concatSourceNode=function(_609,node,_60a){
if(node){
this.rootNode.add(new _5dc.SourceNode(node.loc.start.line,node.loc.start.column,node.loc.source,_609,_60a));
}else{
this.rootNode.add(_609);
}
if(!this.notEmpty){
this.notEmpty=true;
}
};
_2f7.prototype.concatFormat=function(_60b){
if(!_60b){
return;
}
var _60c=_60b.split("\n"),size=_60c.length;
if(size>1){
this.concat(_60c[0]);
for(var i=1;i<size;i++){
var line=_60c[i];
this.concat("\n");
if(line.slice(0,1)==="\\"){
var _60d=1;
var _60e=line.slice(1,1+_60d);
if(_60e==="-"){
_60d=2;
_60e=line.slice(1,1+_60d);
}
var _60f=parseInt(_60e);
if(_60f){
this.concat(_60f>0?_610+(Array(_60f*_611+1)).join(_612):_610.substring(_613*-_60f));
}
line=line.slice(1+_60d);
}else{
if(line||i===size-1){
this.concat(_610);
}
}
if(line){
this.concat(line);
}
}
}else{
this.concat(_60b);
}
};
_2f7.prototype.isEmptyString=function(){
return this.atoms.length!==0;
};
_2f7.prototype.isEmptySourceNode=function(){
return this.notEmpty;
};
_2f7.prototype.appendStringBufferString=function(_614){
this.atoms.push.apply(this.atoms,_614.atoms);
};
_2f7.prototype.appendStringBufferSourceNode=function(_615){
this.rootNode.add(_615.rootNode);
};
_2f7.prototype.lengthString=function(){
return this.atoms.length;
};
_2f7.prototype.lengthSourceNode=function(){
return this.rootNode.children.length;
};
var _616=function(_617,name,_618,_619,_61a,_61b,_61c){
this.name=name;
if(_618){
this.superClass=_618;
}
if(_619){
this.ivars=_619;
}
if(_617){
this.instanceMethods=_61a||Object.create(null);
this.classMethods=_61b||Object.create(null);
}
if(_61c){
this.protocols=_61c;
}
};
_616.prototype.addInstanceMethod=function(_61d){
this.instanceMethods[_61d.name]=_61d;
};
_616.prototype.addClassMethod=function(_61e){
this.classMethods[_61e.name]=_61e;
};
_616.prototype.listOfNotImplementedMethodsForProtocols=function(_61f){
var _620=[],_621=this.getInstanceMethods(),_622=this.getClassMethods();
for(var i=0,size=_61f.length;i<size;i++){
var _623=_61f[i],_624=_623.requiredInstanceMethods,_625=_623.requiredClassMethods,_626=_623.protocols;
if(_624){
for(var _627 in _624){
var _628=_624[_627];
if(!_621[_627]){
_620.push({"methodDef":_628,"protocolDef":_623});
}
}
}
if(_625){
for(var _627 in _625){
var _628=_625[_627];
if(!_622[_627]){
_620.push({"methodDef":_628,"protocolDef":_623});
}
}
}
if(_626){
_620=_620.concat(this.listOfNotImplementedMethodsForProtocols(_626));
}
}
return _620;
};
_616.prototype.getInstanceMethod=function(name){
var _629=this.instanceMethods;
if(_629){
var _62a=_629[name];
if(_62a){
return _62a;
}
}
var _62b=this.superClass;
if(_62b){
return _62b.getInstanceMethod(name);
}
return null;
};
_616.prototype.getClassMethod=function(name){
var _62c=this.classMethods;
if(_62c){
var _62d=_62c[name];
if(_62d){
return _62d;
}
}
var _62e=this.superClass;
if(_62e){
return _62e.getClassMethod(name);
}
return null;
};
_616.prototype.getInstanceMethods=function(){
var _62f=this.instanceMethods;
if(_62f){
var _630=this.superClass,_631=Object.create(null);
if(_630){
var _632=_630.getInstanceMethods();
for(var _633 in _632){
_631[_633]=_632[_633];
}
}
for(var _633 in _62f){
_631[_633]=_62f[_633];
}
return _631;
}
return [];
};
_616.prototype.getClassMethods=function(){
var _634=this.classMethods;
if(_634){
var _635=this.superClass,_636=Object.create(null);
if(_635){
var _637=_635.getClassMethods();
for(var _638 in _637){
_636[_638]=_637[_638];
}
}
for(var _638 in _634){
_636[_638]=_634[_638];
}
return _636;
}
return [];
};
var _639=function(name,_63a,_63b,_63c){
this.name=name;
this.protocols=_63a;
if(_63b){
this.requiredInstanceMethods=_63b;
}
if(_63c){
this.requiredClassMethods=_63c;
}
};
_639.prototype.addInstanceMethod=function(_63d){
(this.requiredInstanceMethods||(this.requiredInstanceMethods=Object.create(null)))[_63d.name]=_63d;
};
_639.prototype.addClassMethod=function(_63e){
(this.requiredClassMethods||(this.requiredClassMethods=Object.create(null)))[_63e.name]=_63e;
};
_639.prototype.getInstanceMethod=function(name){
var _63f=this.requiredInstanceMethods;
if(_63f){
var _640=_63f[name];
if(_640){
return _640;
}
}
var _641=this.protocols;
for(var i=0,size=_641.length;i<size;i++){
var _642=_641[i],_640=_642.getInstanceMethod(name);
if(_640){
return _640;
}
}
return null;
};
_639.prototype.getClassMethod=function(name){
var _643=this.requiredClassMethods;
if(_643){
var _644=_643[name];
if(_644){
return _644;
}
}
var _645=this.protocols;
for(var i=0,size=_645.length;i<size;i++){
var _646=_645[i],_644=_646.getClassMethod(name);
if(_644){
return _644;
}
}
return null;
};
var _647=function(name){
this.name=name;
};
var _648=function(name,_649){
this.name=name;
this.types=_649;
};
var _64a=_5db.makePredicate("self _cmd undefined localStorage arguments");
var _64b=_5db.makePredicate("delete in instanceof new typeof void");
var _64c=_5db.makePredicate("LogicalExpression BinaryExpression");
var _64d=_5db.makePredicate("in instanceof");
var _64e={acornOptions:function(){
return Object.create(null);
},sourceMap:false,sourceMapIncludeSource:false,pass:2,classDefs:function(){
return Object.create(null);
},protocolDefs:function(){
return Object.create(null);
},typeDefs:function(){
return Object.create(null);
},generate:true,generateObjJ:false,formatDescription:null,indentationSpaces:4,indentationType:" ",includeComments:false,transformNamedFunctionDeclarationToAssignment:false,includeMethodFunctionNames:true,includeMethodArgumentTypeSignatures:true,includeIvarTypeSignatures:true,inlineMsgSendFunctions:true,macros:null};
function _64f(opts){
var _650=Object.create(null);
for(var opt in _64e){
if(opts&&Object.prototype.hasOwnProperty.call(opts,opt)){
var _651=opts[opt];
_650[opt]=typeof _651==="function"?_651():_651;
}else{
if(_64e.hasOwnProperty(opt)){
var _652=_64e[opt];
_650[opt]=typeof _652==="function"?_652():_652;
}
}
}
return _650;
};
var _653=function(_654,aURL,_655){
this.source=_654;
this.URL=aURL&&aURL.toString();
_655=_64f(_655);
this.options=_655;
this.pass=_655.pass;
this.classDefs=_655.classDefs;
this.protocolDefs=_655.protocolDefs;
this.typeDefs=_655.typeDefs;
this.generate=_655.generate;
this.createSourceMap=_655.sourceMap;
this.formatDescription=_655.formatDescription;
this.includeComments=_655.includeComments;
this.transformNamedFunctionDeclarationToAssignment=_655.transformNamedFunctionDeclarationToAssignment;
this.jsBuffer=new _2f7(this.createSourceMap,aURL,_655.sourceMap&&_655.sourceMapIncludeSource?this.source:null);
this.imBuffer=null;
this.cmBuffer=null;
this.dependencies=[];
this.warningsAndErrors=[];
this.lastPos=0;
var _656=_655.acornOptions;
if(_656){
if(this.URL){
_656.sourceFile=this.URL.substr(this.URL.lastIndexOf("/")+1);
}
if(_655.sourceMap&&!_656.locations){
_656.locations=true;
}
}else{
_656=_655.acornOptions=this.URL&&{sourceFile:this.URL.substr(this.URL.lastIndexOf("/")+1)};
if(_655.sourceMap){
_656.locations=true;
}
}
if(_655.macros){
if(_656.macros){
_656.macros.concat(_655.macros);
}else{
_656.macros=_655.macros;
}
}
try{
this.tokens=_5db.parse(_654,_655.acornOptions);
(this.pass===2&&(_655.includeComments||_655.formatDescription)?_657:_658)(this.tokens,new _5dd(null,{compiler:this}),this.pass===2?_659:_65a);
}
catch(e){
if(e.lineStart!=null){
e.messageForLine=_654.substring(e.lineStart,e.lineEnd);
}
this.addWarning(e);
return;
}
this.setCompiledCode(this.jsBuffer);
};
_653.prototype.setCompiledCode=function(_65b){
if(this.createSourceMap){
var s=_65b.toString();
this.compiledCode=s.code;
this.sourceMap=s.map;
}else{
this.compiledCode=_65b.toString();
}
};
_5da.compileToExecutable=function(_65c,aURL,_65d){
_5da.currentCompileFile=aURL;
return (new _653(_65c,aURL,_65d)).executable();
};
_5da.compileToIMBuffer=function(_65e,aURL,_65f){
return (new _653(_65e,aURL,_65f)).IMBuffer();
};
_5da.compile=function(_660,aURL,_661){
return new _653(_660,aURL,_661);
};
_5da.compileFileDependencies=function(_662,aURL,_663){
_5da.currentCompileFile=aURL;
(_663||(_663={})).pass=1;
return new _653(_662,aURL,_663);
};
_653.prototype.compilePass2=function(){
var _664=this.options;
_5da.currentCompileFile=this.URL;
this.pass=_664.pass=2;
this.jsBuffer=new _2f7(this.createSourceMap,this.URL,_664.sourceMap&&_664.sourceMapIncludeSource?this.source:null);
if(this.createSourceMap){
this.jsBuffer.concat("\n\n");
}
this.warningsAndErrors=[];
try{
_658(this.tokens,new _5dd(null,{compiler:this}),_659);
}
catch(e){
this.addWarning(e);
return null;
}
this.setCompiledCode(this.jsBuffer);
return this.compiledCode;
};
_653.prototype.addWarning=function(_665){
if(_665.path==null){
_665.path=this.URL;
}
this.warningsAndErrors.push(_665);
};
_653.prototype.getIvarForClass=function(_666,_667){
var ivar=_667.getIvarForCurrentClass(_666);
if(ivar){
return ivar;
}
var c=this.getClassDef(_667.currentClassName());
while(c){
var _668=c.ivars;
if(_668){
var _669=_668[_666];
if(_669){
return _669;
}
}
c=c.superClass;
}
};
_653.prototype.getClassDef=function(_66a){
if(!_66a){
return null;
}
var c=this.classDefs[_66a];
if(c){
return c;
}
if(typeof objj_getClass==="function"){
var _66b=objj_getClass(_66a);
if(_66b){
var _66c=class_copyIvarList(_66b),_66d=_66c.length,_66e=Object.create(null),_66f=class_copyProtocolList(_66b),_670=_66f.length,_671=Object.create(null),_672=_653.methodDefsFromMethodList(class_copyMethodList(_66b)),_673=_653.methodDefsFromMethodList(class_copyMethodList(_66b.isa)),_674=class_getSuperclass(_66b);
for(var i=0;i<_66d;i++){
var ivar=_66c[i];
_66e[ivar.name]={"type":ivar.type,"name":ivar.name};
}
for(var i=0;i<_670;i++){
var _675=_66f[i],_676=protocol_getName(_675),_677=this.getProtocolDef(_676);
_671[_676]=_677;
}
c=new _616(true,_66a,_674?this.getClassDef(_674.name):null,_66e,_672,_673,_671);
this.classDefs[_66a]=c;
return c;
}
}
return null;
};
_653.prototype.getProtocolDef=function(_678){
if(!_678){
return null;
}
var p=this.protocolDefs[_678];
if(p){
return p;
}
if(typeof objj_getProtocol==="function"){
var _679=objj_getProtocol(_678);
if(_679){
var _67a=protocol_getName(_679),_67b=protocol_copyMethodDescriptionList(_679,true,true),_67c=_653.methodDefsFromMethodList(_67b),_67d=protocol_copyMethodDescriptionList(_679,true,false),_67e=_653.methodDefsFromMethodList(_67d),_67f=_679.protocols,_680=[];
if(_67f){
for(var i=0,size=_67f.length;i<size;i++){
_680.push(compiler.getProtocolDef(_67f[i].name));
}
}
p=new _639(_67a,_680,_67c,_67e);
this.protocolDefs[_678]=p;
return p;
}
}
return null;
};
_653.prototype.getTypeDef=function(_681){
if(!_681){
return null;
}
var t=this.typeDefs[_681];
if(t){
return t;
}
if(typeof objj_getTypeDef==="function"){
var _682=objj_getTypeDef(_681);
if(_682){
var _683=typeDef_getName(_682);
t=new _647(_683);
this.typeDefs[_683]=t;
return t;
}
}
return null;
};
_5da.parseGccCompilerFlags=function(_684){
var args=(_684||"").split(" "),_685=args.length,_686={};
for(var _687=0;_687<_685;++_687){
var _688=args[_687];
if(_688.indexOf("-g")===0){
_686.includeMethodFunctionNames=true;
}else{
if(_688.indexOf("-O")===0){
_686.inlineMsgSendFunctions=true;
if(_688.length>2){
_686.inlineMsgSendFunctions=true;
}
}else{
if(_688.indexOf("-T")===0){
_686.includeIvarTypeSignatures=false;
_686.includeMethodArgumentTypeSignatures=false;
}else{
if(_688.indexOf("-S")===0){
_686.sourceMap=true;
_686.sourceMapIncludeSource=true;
}else{
if(_688.indexOf("--include")===0){
var _689=args[++_687],_68a=_689&&_689.charCodeAt(0);
if(_68a===34||_68a===39){
_689=_689.substring(1,_689.length-1);
}
(_686.includeFiles||(_686.includeFiles=[])).push(_689);
}else{
if(_688.indexOf("-D")===0){
var _68b=_688.substring(2);
(_686.macros||(_686.macros=[])).push(_68b);
}
}
}
}
}
}
}
return _686;
};
_653.methodDefsFromMethodList=function(_68c){
var _68d=_68c.length,_68e=Object.create(null);
for(var i=0;i<_68d;i++){
var _68f=_68c[i],_690=method_getName(_68f);
_68e[_690]=new _648(_690,_68f.types);
}
return _68e;
};
_653.prototype.executable=function(){
if(!this._executable){
this._executable=new _306(this.jsBuffer?this.jsBuffer.toString():null,this.dependencies,this.URL,null,this);
}
return this._executable;
};
_653.prototype.IMBuffer=function(){
return this.imBuffer;
};
_653.prototype.code=function(){
return this.compiledCode;
};
_653.prototype.ast=function(){
return JSON.stringify(this.tokens,null,_611);
};
_653.prototype.map=function(){
return JSON.stringify(this.sourceMap);
};
_653.prototype.prettifyMessage=function(_691){
var line=_691.messageForLine,_692="\n"+(line||"");
_692+=(new Array((_691.messageOnColumn||0)+1)).join(" ");
if(line){
_692+=(new Array(Math.min(1,line.length||1)+1)).join("^")+"\n";
}
_692+=_691.messageType+" line "+_691.messageOnLine+" in "+this.URL+": "+_691.message;
return _692;
};
_653.prototype.error_message=function(_693,node){
var pos=_5db.getLineInfo(this.source,node.start),_694=new SyntaxError(_693);
_694.messageOnLine=pos.line;
_694.messageOnColumn=pos.column;
_694.path=this.URL;
_694.messageForNode=node;
_694.messageType="ERROR";
_694.messageForLine=this.source.substring(pos.lineStart,pos.lineEnd);
return _694;
};
_653.prototype.pushImport=function(url){
if(!_653.importStack){
_653.importStack=[];
}
_653.importStack.push(url);
};
_653.prototype.popImport=function(){
_653.importStack.pop();
};
function _600(_695,node,code){
var _696=_5db.getLineInfo(code,node.start);
_696.message=_695;
_696.messageOnLine=_696.line;
_696.messageOnColumn=_696.column;
_696.messageForNode=node;
_696.messageType="WARNING";
_696.messageForLine=code.substring(_696.lineStart,_696.lineEnd);
return _696;
};
function _658(node,_697,_698){
function c(node,st,_699){
_698[_699||node.type](node,st,c);
};
c(node,_697);
};
function _657(node,_69a,_69b){
var _69c,_69d;
function c(node,st,_69e){
var _69f=st.compiler,_6a0=_69f.includeComments,_6a1=st.currentNode(),_6a2=_69c,_6a3=_6a2===node;
_69c=node;
if(_6a0&&!_6a3&&node.commentsBefore&&node.commentsBefore!==_69d){
for(var i=0;i<node.commentsBefore.length;i++){
_69f.jsBuffer.concat(node.commentsBefore[i]);
}
}
st.pushNode(node,_69e);
var _6a4=st.formatDescription();
if(!_6a3&&_6a4&&_6a4.before){
_69f.jsBuffer.concatFormat(_6a4.before);
}
_69b[_69e||node.type](node,st,c,_6a4);
if(!_6a3&&_6a4&&_6a4.after){
_69f.jsBuffer.concatFormat(_6a4.after);
}
st.popNode();
if(_6a0&&!_6a3&&node.commentsAfter){
for(var i=0;i<node.commentsAfter.length;i++){
_69f.jsBuffer.concat(node.commentsAfter[i]);
}
_69d=node.commentsAfter;
}else{
_69d=null;
}
};
c(node,_69a);
};
function _6a5(node){
switch(node.type){
case "Literal":
case "Identifier":
return true;
case "ArrayExpression":
for(var i=0;i<node.elements.length;++i){
if(!_6a5(node.elements[i])){
return false;
}
}
return true;
case "DictionaryLiteral":
for(var i=0;i<node.keys.length;++i){
if(!_6a5(node.keys[i])){
return false;
}
if(!_6a5(node.values[i])){
return false;
}
}
return true;
case "ObjectExpression":
for(var i=0;i<node.properties.length;++i){
if(!_6a5(node.properties[i].value)){
return false;
}
}
return true;
case "FunctionExpression":
for(var i=0;i<node.params.length;++i){
if(!_6a5(node.params[i])){
return false;
}
}
return true;
case "SequenceExpression":
for(var i=0;i<node.expressions.length;++i){
if(!_6a5(node.expressions[i])){
return false;
}
}
return true;
case "UnaryExpression":
return _6a5(node.argument);
case "BinaryExpression":
return _6a5(node.left)&&_6a5(node.right);
case "ConditionalExpression":
return _6a5(node.test)&&_6a5(node.consequent)&&_6a5(node.alternate);
case "MemberExpression":
return _6a5(node.object)&&(!node.computed||_6a5(node.property));
case "Dereference":
return _6a5(node.expr);
case "Reference":
return _6a5(node.element);
default:
return false;
}
};
function _6a6(st,node){
if(!_6a5(node)){
throw st.compiler.error_message("Dereference of expression with side effects",node);
}
};
function _6a7(c){
return function(node,st,_6a8,_6a9){
st.compiler.jsBuffer.concat("(");
c(node,st,_6a8,_6a9);
st.compiler.jsBuffer.concat(")");
};
};
var _6aa={"*":3,"/":3,"%":3,"+":4,"-":4,"<<":5,">>":5,">>>":5,"<":6,"<=":6,">":6,">=":6,"in":6,"instanceof":6,"==":7,"!=":7,"===":7,"!==":7,"&":8,"^":9,"|":10,"&&":11,"||":12};
var _6ab={MemberExpression:0,CallExpression:1,NewExpression:2,FunctionExpression:3,UnaryExpression:4,UpdateExpression:4,BinaryExpression:5,LogicalExpression:6,ConditionalExpression:7,AssignmentExpression:8};
function _6ac(node,_6ad,_6ae){
var _6af=node.type,_6ac=_6ab[_6af]||-1,_6b0=_6ab[_6ad.type]||-1,_6b1,_6b2;
return _6ac<_6b0||_6ac===_6b0&&_64c(_6af)&&((_6b1=_6aa[node.operator])<(_6b2=_6aa[_6ad.operator])||_6ae&&_6b1===_6b2);
};
var _65a=walk.make({ImportStatement:function(node,st,c){
var _6b3=node.filename.value;
st.compiler.dependencies.push({url:_6b3,isLocal:node.localfilepath});
}});
var _612=" ";
var _611=4;
var _613=_611*_612.length;
var _6b4=(Array(_611+1)).join(_612);
var _610="";
var _659=walk.make({Program:function(node,st,c){
var _6b5=st.compiler,_6b6=_6b5.generate;
_612=_6b5.options.indentationType;
_611=_6b5.options.indentationSpaces;
_613=_611*_612.length;
_6b4=(Array(_611+1)).join(_612);
_610="";
for(var i=0;i<node.body.length;++i){
c(node.body[i],st,"Statement");
}
if(!_6b6){
_6b5.jsBuffer.concat(_6b5.source.substring(_6b5.lastPos,node.end));
}
var _6b7=st.maybeWarnings();
if(_6b7){
for(var i=0;i<_6b7.length;i++){
var _6b8=_6b7[i];
if(_6b8.checkIfWarning(st)){
_6b5.addWarning(_6b8.message);
}
}
}
},BlockStatement:function(node,st,c,_6b9){
var _6ba=st.compiler,_6bb=_6ba.generate,_6bc=st.endOfScopeBody,_6bd;
if(_6bc){
delete st.endOfScopeBody;
}
if(_6bb){
var _6be=st.skipIndentation;
_6bd=_6ba.jsBuffer;
if(_6b9){
_6bd.concat("{",node);
_6bd.concatFormat(_6b9.afterLeftBrace);
}else{
if(_6be){
delete st.skipIndentation;
}else{
_6bd.concat(_610.substring(_613));
}
_6bd.concat("{\n",node);
}
}
for(var i=0;i<node.body.length;++i){
c(node.body[i],st,"Statement");
}
if(_6bb){
var _6bf=st.maxReceiverLevel;
if(_6bc&&_6bf){
_6bd.concat(_610);
_6bd.concat("var ");
for(var i=0;i<_6bf;i++){
if(i){
_6bd.concat(", ");
}
_6bd.concat("___r");
_6bd.concat(i+1+"");
}
_6bd.concat(";\n");
}
if(_6b9){
_6bd.concatFormat(_6b9.beforeRightBrace);
_6bd.concat("}",node);
}else{
_6bd.concat(_610.substring(_613));
_6bd.concat("}",node);
if(!_6be&&st.isDecl!==false){
_6bd.concat("\n");
}
st.indentBlockLevel--;
}
}
},ExpressionStatement:function(node,st,c,_6c0){
var _6c1=st.compiler,_6c2=_6c1.generate&&!_6c0;
if(_6c2){
_6c1.jsBuffer.concat(_610);
}
c(node.expression,st,"Expression");
if(_6c2){
_6c1.jsBuffer.concat(";\n");
}
},IfStatement:function(node,st,c,_6c3){
var _6c4=st.compiler,_6c5=_6c4.generate,_6c6;
if(_6c5){
_6c6=_6c4.jsBuffer;
if(_6c3){
_6c6.concat("if",node);
_6c6.concatFormat(_6c3.beforeLeftParenthesis);
_6c6.concat("(");
}else{
if(!st.superNodeIsElse){
_6c6.concat(_610);
}else{
delete st.superNodeIsElse;
}
_6c6.concat("if (",node);
}
}
c(node.test,st,"Expression");
if(_6c5){
if(_6c3){
_6c6.concat(")",node);
_6c6.concatFormat(_6c3.afterRightParenthesis);
}else{
_6c6.concat(node.consequent.type==="EmptyStatement"?");\n":")\n",node);
}
}
_610+=_6b4;
c(node.consequent,st,"Statement");
_610=_610.substring(_613);
var _6c7=node.alternate;
if(_6c7){
var _6c8=_6c7.type!=="IfStatement";
if(_6c5){
if(_6c3){
_6c6.concatFormat(_6c3.beforeElse);
_6c6.concat("else",node);
_6c6.concatFormat(_6c3.afterElse);
}else{
var _6c9=_6c7.type==="EmptyStatement";
_6c6.concat(_610);
_6c6.concat(_6c8?_6c9?"else;\n":"else\n":"else ",node);
}
}
if(_6c8){
_610+=_6b4;
}else{
st.superNodeIsElse=true;
}
c(_6c7,st,"Statement");
if(_6c8){
_610=_610.substring(_613);
}
}
},LabeledStatement:function(node,st,c,_6ca){
var _6cb=st.compiler;
if(_6cb.generate){
var _6cc=_6cb.jsBuffer;
if(!_6ca){
_6cc.concat(_610);
}
c(node.label,st,"IdentifierName");
if(_6ca){
_6cc.concat(":",node);
_6cc.concatFormat(_6ca.afterColon);
}else{
_6cc.concat(": ",node);
}
}
c(node.body,st,"Statement");
},BreakStatement:function(node,st,c,_6cd){
var _6ce=st.compiler;
if(_6ce.generate){
var _6cf=node.label,_6d0=_6ce.jsBuffer;
if(!_6cd){
_6d0.concat(_610);
}
if(_6cf){
if(_6cd){
_6d0.concat("break",node);
_6d0.concatFormat(_6cd.beforeLabel);
}else{
_6d0.concat("break ",node);
}
c(_6cf,st,"IdentifierName");
if(!_6cd){
_6d0.concat(";\n");
}
}else{
_6d0.concat(_6cd?"break":"break;\n",node);
}
}
},ContinueStatement:function(node,st,c,_6d1){
var _6d2=st.compiler;
if(_6d2.generate){
var _6d3=node.label,_6d4=_6d2.jsBuffer;
if(!_6d1){
_6d4.concat(_610);
}
if(_6d3){
if(_6d1){
_6d4.concat("continue",node);
_6d4.concatFormat(_6d1.beforeLabel);
}else{
_6d4.concat("continue ",node);
}
c(_6d3,st,"IdentifierName");
if(!_6d1){
_6d4.concat(";\n");
}
}else{
_6d4.concat(_6d1?"continue":"continue;\n",node);
}
}
},WithStatement:function(node,st,c,_6d5){
var _6d6=st.compiler,_6d7=_6d6.generate,_6d8;
if(_6d7){
_6d8=_6d6.jsBuffer;
if(_6d5){
_6d8.concat("with",node);
_6d8.concatFormat(_6d5.beforeLeftParenthesis);
_6d8.concat("(");
}else{
_6d8.concat(_610);
_6d8.concat("with(",node);
}
}
c(node.object,st,"Expression");
if(_6d7){
if(_6d5){
_6d8.concat(")",node);
_6d8.concatFormat(_6d5.afterRightParenthesis);
}else{
_6d8.concat(")\n",node);
}
}
_610+=_6b4;
c(node.body,st,"Statement");
_610=_610.substring(_613);
},SwitchStatement:function(node,st,c,_6d9){
var _6da=st.compiler,_6db=_6da.generate,_6dc;
if(_6db){
_6dc=_6da.jsBuffer;
if(_6d9){
_6dc.concat("switch",node);
_6dc.concatFormat(_6d9.beforeLeftParenthesis);
_6dc.concat("(",node);
}else{
_6dc.concat(_610);
_6dc.concat("switch(",node);
}
}
c(node.discriminant,st,"Expression");
if(_6db){
if(_6d9){
_6dc.concat(")");
_6dc.concatFormat(_6d9.afterRightParenthesis);
_6dc.concat("{");
_6dc.concatFormat(_6d9.afterLeftBrace);
}else{
_6dc.concat(") {\n");
}
}
_610+=_6b4;
for(var i=0;i<node.cases.length;++i){
var cs=node.cases[i];
if(cs.test){
if(_6db){
if(_6d9){
_6dc.concatFormat(_6d9.beforeCase);
_6dc.concat("case",node);
_6dc.concatFormat(_6d9.afterCase);
}else{
_6dc.concat(_610);
_6dc.concat("case ");
}
}
c(cs.test,st,"Expression");
if(_6db){
if(_6d9){
_6dc.concat(":");
_6dc.concatFormat(_6d9.afterColon);
}else{
_6dc.concat(":\n");
}
}
}else{
if(_6db){
if(_6d9){
_6dc.concatFormat(_6d9.beforeCase);
_6dc.concat("default");
_6dc.concatFormat(_6d9.afterCase);
_6dc.concat(":");
_6dc.concatFormat(_6d9.afterColon);
}else{
_6dc.concat("default:\n");
}
}
}
_610+=_6b4;
for(var j=0;j<cs.consequent.length;++j){
c(cs.consequent[j],st,"Statement");
}
_610=_610.substring(_613);
}
_610=_610.substring(_613);
if(_6db){
if(_6d9){
_6dc.concatFormat(_6d9.beforeRightBrace);
_6dc.concat("}");
}else{
_6dc.concat(_610);
_6dc.concat("}\n");
}
}
},ReturnStatement:function(node,st,c,_6dd){
var _6de=st.compiler,_6df=_6de.generate,_6e0;
if(_6df){
_6e0=_6de.jsBuffer;
if(!_6dd){
_6e0.concat(_610);
}
_6e0.concat("return",node);
}
if(node.argument){
if(_6df){
_6e0.concatFormat(_6dd?_6dd.beforeExpression:" ");
}
c(node.argument,st,"Expression");
}
if(_6df&&!_6dd){
_6e0.concat(";\n");
}
},ThrowStatement:function(node,st,c,_6e1){
var _6e2=st.compiler,_6e3=_6e2.generate,_6e4;
if(_6e3){
_6e4=_6e2.jsBuffer;
if(!_6e1){
_6e4.concat(_610);
}
_6e4.concat("throw",node);
_6e4.concatFormat(_6e1?_6e1.beforeExpression:" ");
}
c(node.argument,st,"Expression");
if(_6e3&&!_6e1){
_6e4.concat(";\n");
}
},TryStatement:function(node,st,c,_6e5){
var _6e6=st.compiler,_6e7=_6e6.generate,_6e8;
if(_6e7){
_6e8=_6e6.jsBuffer;
if(!_6e5){
_6e8.concat(_610);
}
_6e8.concat("try",node);
_6e8.concatFormat(_6e5?_6e5.beforeStatement:" ");
}
_610+=_6b4;
if(!_6e5){
st.skipIndentation=true;
}
c(node.block,st,"Statement");
_610=_610.substring(_613);
if(node.handler){
var _6e9=node.handler,_6ea=new _5dd(st),_6eb=_6e9.param,name=_6eb.name;
_6ea.vars[name]={type:"catch clause",node:_6eb};
if(_6e7){
if(_6e5){
_6e8.concatFormat(_6e5.beforeCatch);
_6e8.concat("catch");
_6e8.concatFormat(_6e5.afterCatch);
_6e8.concat("(");
c(_6eb,st,"IdentifierName");
_6e8.concat(")");
_6e8.concatFormat(_6e5.beforeCatchStatement);
}else{
_6e8.concat("\n");
_6e8.concat(_610);
_6e8.concat("catch(");
_6e8.concat(name);
_6e8.concat(") ");
}
}
_610+=_6b4;
_6ea.skipIndentation=true;
_6ea.endOfScopeBody=true;
c(_6e9.body,_6ea,"ScopeBody");
_610=_610.substring(_613);
_6ea.copyAddedSelfToIvarsToParent();
}
if(node.finalizer){
if(_6e7){
if(_6e5){
_6e8.concatFormat(_6e5.beforeCatch);
_6e8.concat("finally");
_6e8.concatFormat(_6e5.beforeCatchStatement);
}else{
_6e8.concat("\n");
_6e8.concat(_610);
_6e8.concat("finally ");
}
}
_610+=_6b4;
st.skipIndentation=true;
c(node.finalizer,st,"Statement");
_610=_610.substring(_613);
}
if(_6e7&&!_6e5){
_6e8.concat("\n");
}
},WhileStatement:function(node,st,c,_6ec){
var _6ed=st.compiler,_6ee=_6ed.generate,body=node.body,_6ef;
if(_6ee){
_6ef=_6ed.jsBuffer;
if(_6ec){
_6ef.concat("while",node);
_6ef.concatFormat(_6ec.beforeLeftParenthesis);
_6ef.concat("(");
}else{
_6ef.concat(_610);
_6ef.concat("while (",node);
}
}
c(node.test,st,"Expression");
if(_6ee){
if(_6ec){
_6ef.concat(")");
_6ef.concatFormat(_6ec.afterRightParenthesis);
}else{
_6ef.concat(body.type==="EmptyStatement"?");\n":")\n");
}
}
_610+=_6b4;
c(body,st,"Statement");
_610=_610.substring(_613);
},DoWhileStatement:function(node,st,c,_6f0){
var _6f1=st.compiler,_6f2=_6f1.generate,_6f3;
if(_6f2){
_6f3=_6f1.jsBuffer;
if(_6f0){
_6f3.concat("do",node);
_6f3.concatFormat(_6f0.beforeStatement);
}else{
_6f3.concat(_610);
_6f3.concat("do\n",node);
}
}
_610+=_6b4;
c(node.body,st,"Statement");
_610=_610.substring(_613);
if(_6f2){
if(_6f0){
_6f3.concat("while");
_6f3.concatFormat(_6f0.beforeLeftParenthesis);
_6f3.concat("(");
}else{
_6f3.concat(_610);
_6f3.concat("while (");
}
}
c(node.test,st,"Expression");
if(_6f2){
_6f3.concatFormat(_6f0?")":");\n");
}
},ForStatement:function(node,st,c,_6f4){
var _6f5=st.compiler,_6f6=_6f5.generate,body=node.body,_6f7;
if(_6f6){
_6f7=_6f5.jsBuffer;
if(_6f4){
_6f7.concat("for",node);
_6f7.concatFormat(_6f4.beforeLeftParenthesis);
_6f7.concat("(");
}else{
_6f7.concat(_610);
_6f7.concat("for (",node);
}
}
if(node.init){
c(node.init,st,"ForInit");
}
if(_6f6){
_6f7.concat(_6f4?";":"; ");
}
if(node.test){
c(node.test,st,"Expression");
}
if(_6f6){
_6f7.concat(_6f4?";":"; ");
}
if(node.update){
c(node.update,st,"Expression");
}
if(_6f6){
if(_6f4){
_6f7.concat(")");
_6f7.concatFormat(_6f4.afterRightParenthesis);
}else{
_6f7.concat(body.type==="EmptyStatement"?");\n":")\n");
}
}
_610+=_6b4;
c(body,st,"Statement");
_610=_610.substring(_613);
},ForInStatement:function(node,st,c,_6f8){
var _6f9=st.compiler,_6fa=_6f9.generate,body=node.body,_6fb;
if(_6fa){
_6fb=_6f9.jsBuffer;
if(_6f8){
_6fb.concat("for",node);
_6fb.concatFormat(_6f8.beforeLeftParenthesis);
_6fb.concat("(");
}else{
_6fb.concat(_610);
_6fb.concat("for (",node);
}
}
c(node.left,st,"ForInit");
if(_6fa){
if(_6f8){
_6fb.concatFormat(_6f8.beforeIn);
_6fb.concat("in");
_6fb.concatFormat(_6f8.afterIn);
}else{
_6fb.concat(" in ");
}
}
c(node.right,st,"Expression");
if(_6fa){
if(_6f8){
_6fb.concat(")");
_6fb.concatFormat(_6f8.afterRightParenthesis);
}else{
_6fb.concat(body.type==="EmptyStatement"?");\n":")\n");
}
}
_610+=_6b4;
c(body,st,"Statement");
_610=_610.substring(_613);
},ForInit:function(node,st,c){
var _6fc=st.compiler,_6fd=_6fc.generate;
if(node.type==="VariableDeclaration"){
st.isFor=true;
c(node,st);
delete st.isFor;
}else{
c(node,st,"Expression");
}
},DebuggerStatement:function(node,st,c,_6fe){
var _6ff=st.compiler;
if(_6ff.generate){
var _700=_6ff.jsBuffer;
if(_6fe){
_700.concat("debugger",node);
}else{
_700.concat(_610);
_700.concat("debugger;\n",node);
}
}
},Function:function(node,st,c,_701){
var _702=st.compiler,_703=_702.generate,_704=_702.jsBuffer,_705=new _5dd(st),decl=node.type=="FunctionDeclaration",id=node.id;
_705.isDecl=decl;
for(var i=0;i<node.params.length;++i){
_705.vars[node.params[i].name]={type:"argument",node:node.params[i]};
}
if(_703&&!_701){
_704.concat(_610);
}
if(id){
var name=id.name;
(decl?st:_705).vars[name]={type:decl?"function":"function name",node:id};
if(_702.transformNamedFunctionDeclarationToAssignment){
if(_703){
_704.concat(name);
_704.concat(" = ");
}else{
_704.concat(_702.source.substring(_702.lastPos,node.start));
_704.concat(name);
_704.concat(" = function");
_702.lastPos=id.end;
}
}
}
if(_703){
_704.concat("function",node);
if(!_702.transformNamedFunctionDeclarationToAssignment&&id){
if(!_701){
_704.concat(" ");
}
c(id,st,"IdentifierName");
}
if(_701){
_704.concatFormat(_701.beforeLeftParenthesis);
}
_704.concat("(");
for(var i=0;i<node.params.length;++i){
if(i){
_704.concat(_701?",":", ");
}
c(node.params[i],st,"IdentifierName");
}
if(_701){
_704.concat(")");
_704.concatFormat(_701.afterRightParenthesis);
}else{
_704.concat(")\n");
}
}
_610+=_6b4;
_705.endOfScopeBody=true;
c(node.body,_705,"ScopeBody");
_610=_610.substring(_613);
_705.copyAddedSelfToIvarsToParent();
},VariableDeclaration:function(node,st,c,_706){
var _707=st.compiler,_708=_707.generate,_709;
if(_708){
_709=_707.jsBuffer;
if(!st.isFor&&!_706){
_709.concat(_610);
}
_709.concat(_706?"var":"var ",node);
}
for(var i=0;i<node.declarations.length;++i){
var decl=node.declarations[i],_70a=decl.id.name;
if(i){
if(_708){
if(_706){
_709.concat(",");
}else{
if(st.isFor){
_709.concat(", ");
}else{
_709.concat(",\n");
_709.concat(_610);
_709.concat("    ");
}
}
}
}
st.vars[_70a]={type:"var",node:decl.id};
c(decl.id,st,"IdentifierName");
if(decl.init){
if(_708){
if(_706){
_709.concatFormat(_706.beforeEqual);
_709.concat("=");
_709.concatFormat(_706.afterEqual);
}else{
_709.concat(" = ");
}
}
c(decl.init,st,"Expression");
}
if(st.addedSelfToIvars){
var _70b=st.addedSelfToIvars[_70a];
if(_70b){
var _70c=st.compiler.jsBuffer.atoms;
for(var i=0,size=_70b.length;i<size;i++){
var dict=_70b[i];
_70c[dict.index]="";
_707.addWarning(_600("Local declaration of '"+_70a+"' hides instance variable",dict.node,_707.source));
}
st.addedSelfToIvars[_70a]=[];
}
}
}
if(_708&&!_706&&!st.isFor){
_709.concat(";\n");
}
},ThisExpression:function(node,st,c){
var _70d=st.compiler;
if(_70d.generate){
_70d.jsBuffer.concat("this",node);
}
},ArrayExpression:function(node,st,c,_70e){
var _70f=st.compiler,_710=_70f.generate,_711;
if(_710){
_711=_70f.jsBuffer;
_711.concat("[",node);
}
for(var i=0;i<node.elements.length;++i){
var elt=node.elements[i];
if(_710&&i!==0){
if(_70e){
_711.concatFormat(_70e.beforeComma);
_711.concat(",");
_711.concatFormat(_70e.afterComma);
}else{
_711.concat(", ");
}
}
if(elt){
c(elt,st,"Expression");
}
}
if(_710){
_711.concat("]");
}
},ObjectExpression:function(node,st,c,_712){
var _713=st.compiler,_714=_713.generate,_715=node.properties,_716=_713.jsBuffer;
if(_714){
_716.concat("{",node);
}
for(var i=0,size=_715.length;i<size;++i){
var prop=_715[i];
if(_714){
if(i){
if(_712){
_716.concatFormat(_712.beforeComma);
_716.concat(",");
_716.concatFormat(_712.afterComma);
}else{
_716.concat(", ");
}
}
st.isPropertyKey=true;
c(prop.key,st,"Expression");
delete st.isPropertyKey;
if(_712){
_716.concatFormat(_712.beforeColon);
_716.concat(":");
_716.concatFormat(_712.afterColon);
}else{
_716.concat(": ");
}
}else{
if(prop.key.raw&&prop.key.raw.charAt(0)==="@"){
_716.concat(_713.source.substring(_713.lastPos,prop.key.start));
_713.lastPos=prop.key.start+1;
}
}
c(prop.value,st,"Expression");
}
if(_714){
_716.concat("}");
}
},SequenceExpression:function(node,st,c,_717){
var _718=st.compiler,_719=_718.generate,_71a;
if(_719){
_71a=_718.jsBuffer;
_71a.concat("(",node);
}
for(var i=0;i<node.expressions.length;++i){
if(_719&&i!==0){
if(_717){
_71a.concatFormat(_717.beforeComma);
_71a.concat(",");
_71a.concatFormat(_717.afterComma);
}else{
_71a.concat(", ");
}
}
c(node.expressions[i],st,"Expression");
}
if(_719){
_71a.concat(")");
}
},UnaryExpression:function(node,st,c){
var _71b=st.compiler,_71c=_71b.generate,_71d=node.argument;
if(_71c){
var _71e=_71b.jsBuffer;
if(node.prefix){
_71e.concat(node.operator,node);
if(_64b(node.operator)){
_71e.concat(" ");
}
(_6ac(node,_71d)?_6a7(c):c)(_71d,st,"Expression");
}else{
(_6ac(node,_71d)?_6a7(c):c)(_71d,st,"Expression");
_71e.concat(node.operator);
}
}else{
c(_71d,st,"Expression");
}
},UpdateExpression:function(node,st,c){
var _71f=st.compiler,_720=_71f.generate,_721=_71f.jsBuffer;
if(node.argument.type==="Dereference"){
_6a6(st,node.argument);
if(!_720){
_721.concat(_71f.source.substring(_71f.lastPos,node.start));
}
_721.concat((node.prefix?"":"(")+"(");
if(!_720){
_71f.lastPos=node.argument.expr.start;
}
c(node.argument.expr,st,"Expression");
if(!_720){
_721.concat(_71f.source.substring(_71f.lastPos,node.argument.expr.end));
}
_721.concat(")(");
if(!_720){
_71f.lastPos=node.argument.start;
}
c(node.argument,st,"Expression");
if(!_720){
_721.concat(_71f.source.substring(_71f.lastPos,node.argument.end));
}
_721.concat(" "+node.operator.substring(0,1)+" 1)"+(node.prefix?"":node.operator=="++"?" - 1)":" + 1)"));
if(!_720){
_71f.lastPos=node.end;
}
return;
}
if(node.prefix){
if(_720){
_721.concat(node.operator,node);
if(_64b(node.operator)){
_721.concat(" ");
}
}
(_720&&_6ac(node,node.argument)?_6a7(c):c)(node.argument,st,"Expression");
}else{
(_720&&_6ac(node,node.argument)?_6a7(c):c)(node.argument,st,"Expression");
if(_720){
_721.concat(node.operator);
}
}
},BinaryExpression:function(node,st,c,_722){
var _723=st.compiler,_724=_723.generate,_725=_64d(node.operator);
(_724&&_6ac(node,node.left)?_6a7(c):c)(node.left,st,"Expression");
if(_724){
var _726=_723.jsBuffer;
_726.concatFormat(_722?_722.beforeOperator:" ");
_726.concat(node.operator);
_726.concatFormat(_722?_722.afterOperator:" ");
}
(_724&&_6ac(node,node.right,true)?_6a7(c):c)(node.right,st,"Expression");
},LogicalExpression:function(node,st,c,_727){
var _728=st.compiler,_729=_728.generate;
(_729&&_6ac(node,node.left)?_6a7(c):c)(node.left,st,"Expression");
if(_729){
var _72a=_728.jsBuffer;
_72a.concatFormat(_727?_727.beforeOperator:" ");
_72a.concat(node.operator);
_72a.concatFormat(_727?_727.afterOperator:" ");
}
(_729&&_6ac(node,node.right,true)?_6a7(c):c)(node.right,st,"Expression");
},AssignmentExpression:function(node,st,c,_72b){
var _72c=st.compiler,_72d=_72c.generate,_72e=st.assignment,_72f=_72c.jsBuffer;
if(node.left.type==="Dereference"){
_6a6(st,node.left);
if(!_72d){
_72f.concat(_72c.source.substring(_72c.lastPos,node.start));
}
_72f.concat("(",node);
if(!_72d){
_72c.lastPos=node.left.expr.start;
}
c(node.left.expr,st,"Expression");
if(!_72d){
_72f.concat(_72c.source.substring(_72c.lastPos,node.left.expr.end));
}
_72f.concat(")(");
if(node.operator!=="="){
if(!_72d){
_72c.lastPos=node.left.start;
}
c(node.left,st,"Expression");
if(!_72d){
_72f.concat(_72c.source.substring(_72c.lastPos,node.left.end));
}
_72f.concat(" "+node.operator.substring(0,1)+" ");
}
if(!_72d){
_72c.lastPos=node.right.start;
}
c(node.right,st,"Expression");
if(!_72d){
_72f.concat(_72c.source.substring(_72c.lastPos,node.right.end));
}
_72f.concat(")");
if(!_72d){
_72c.lastPos=node.end;
}
return;
}
var _72e=st.assignment,_730=node.left;
st.assignment=true;
if(_730.type==="Identifier"&&_730.name==="self"){
var lVar=st.getLvar("self",true);
if(lVar){
var _731=lVar.scope;
if(_731){
_731.assignmentToSelf=true;
}
}
}
(_72d&&_6ac(node,_730)?_6a7(c):c)(_730,st,"Expression");
if(_72d){
_72f.concatFormat(_72b?_72b.beforeOperator:" ");
_72f.concat(node.operator);
_72f.concatFormat(_72b?_72b.afterOperator:" ");
}
st.assignment=_72e;
(_72d&&_6ac(node,node.right,true)?_6a7(c):c)(node.right,st,"Expression");
if(st.isRootScope()&&_730.type==="Identifier"&&!st.getLvar(_730.name)){
st.vars[_730.name]={type:"global",node:_730};
}
},ConditionalExpression:function(node,st,c,_732){
var _733=st.compiler,_734=_733.generate,_735;
(_734&&_6ac(node,node.test)?_6a7(c):c)(node.test,st,"Expression");
if(_734){
_735=_733.jsBuffer;
if(_732){
_735.concatFormat(_732.beforeOperator);
_735.concat("?");
_735.concatFormat(_732.afterOperator);
}else{
_735.concat(" ? ");
}
}
c(node.consequent,st,"Expression");
if(_734){
if(_732){
_735.concatFormat(_732.beforeOperator);
_735.concat(":");
_735.concatFormat(_732.afterOperator);
}else{
_735.concat(" : ");
}
}
c(node.alternate,st,"Expression");
},NewExpression:function(node,st,c,_736){
var _737=st.compiler,_738=node.arguments,_739=_737.generate,_73a;
if(_739){
_73a=_737.jsBuffer;
_73a.concat("new ",node);
}
(_739&&_6ac(node,node.callee)?_6a7(c):c)(node.callee,st,"Expression");
if(_739){
_73a.concat("(");
}
if(_738){
for(var i=0,size=_738.length;i<size;++i){
if(i&&_739){
_73a.concatFormat(_736?",":", ");
}
c(_738[i],st,"Expression");
}
}
if(_739){
_73a.concat(")");
}
},CallExpression:function(node,st,c,_73b){
var _73c=st.compiler,_73d=node.arguments,_73e=_73c.generate,_73f=node.callee,_740;
if(_73f.type==="Identifier"&&_73f.name==="eval"){
var _741=st.getLvar("self",true);
if(_741){
var _742=_741.scope;
if(_742){
_742.assignmentToSelf=true;
}
}
}
(_73e&&_6ac(node,_73f)?_6a7(c):c)(_73f,st,"Expression");
if(_73e){
_740=_73c.jsBuffer;
_740.concat("(");
}
if(_73d){
for(var i=0,size=_73d.length;i<size;++i){
if(i&&_73e){
_740.concat(_73b?",":", ");
}
c(_73d[i],st,"Expression");
}
}
if(_73e){
_740.concat(")");
}
},MemberExpression:function(node,st,c){
var _743=st.compiler,_744=_743.generate,_745=node.computed;
(_744&&_6ac(node,node.object)?_6a7(c):c)(node.object,st,"Expression");
if(_744){
_743.jsBuffer.concat(_745?"[":".",node);
}
st.secondMemberExpression=!_745;
(_744&&!_745&&_6ac(node,node.property)?_6a7(c):c)(node.property,st,"Expression");
st.secondMemberExpression=false;
if(_744&&_745){
_743.jsBuffer.concat("]");
}
},Identifier:function(node,st,c){
var _746=st.compiler,_747=_746.generate,_748=node.name;
if(st.currentMethodType()==="-"&&!st.secondMemberExpression&&!st.isPropertyKey){
var lvar=st.getLvar(_748,true),ivar=_746.getIvarForClass(_748,st);
if(ivar){
if(lvar){
_746.addWarning(_600("Local declaration of '"+_748+"' hides instance variable",node,_746.source));
}else{
var _749=node.start;
if(!_747){
do{
_746.jsBuffer.concat(_746.source.substring(_746.lastPos,_749));
_746.lastPos=_749;
}while(_746.source.substr(_749++,1)==="(");
}
((st.addedSelfToIvars||(st.addedSelfToIvars=Object.create(null)))[_748]||(st.addedSelfToIvars[_748]=[])).push({node:node,index:_746.jsBuffer.length()});
_746.jsBuffer.concat("self.",node);
}
}else{
if(!_64a(_748)){
var _74a,_74b=typeof _1[_748]!=="undefined"||typeof window!=="undefined"&&typeof window[_748]!=="undefined"||_746.getClassDef(_748),_74c=st.getLvar(_748);
if(_74b&&(!_74c||_74c.type!=="class")){
}else{
if(!_74c){
if(st.assignment){
_74a=new _5fe("Creating global variable inside function or method '"+_748+"'",node,_746.source);
st.vars[_748]={type:"remove global warning",node:node};
}else{
_74a=new _5fe("Using unknown class or uninitialized global variable '"+_748+"'",node,_746.source);
}
}
}
if(_74a){
st.addMaybeWarning(_74a);
}
}
}
}
if(_747){
_746.jsBuffer.concat(_748,node,"self");
}
},IdentifierName:function(node,st,c){
var _74d=st.compiler;
if(_74d.generate){
_74d.jsBuffer.concat(node.name,node);
}
},Literal:function(node,st,c){
var _74e=st.compiler,_74f=_74e.generate;
if(_74f){
if(node.raw){
if(node.raw.charAt(0)==="@"){
_74e.jsBuffer.concat(node.raw.substring(1),node);
}else{
_74e.jsBuffer.concat(node.raw,node);
}
}else{
var _750=node.value,_751=_750.indexOf("\"")!==-1;
_74e.jsBuffer.concat(_751?"'":"\"",node);
_74e.jsBuffer.concat(_750);
_74e.jsBuffer.concat(_751?"'":"\"");
}
}else{
if(node.raw.charAt(0)==="@"){
_74e.jsBuffer.concat(_74e.source.substring(_74e.lastPos,node.start));
_74e.lastPos=node.start+1;
}
}
},ArrayLiteral:function(node,st,c){
var _752=st.compiler,_753=_752.generate,_754=_752.jsBuffer,_755=_752.options.generateObjJ,_756=node.elements.length;
if(!_753){
_754.concat(_752.source.substring(_752.lastPos,node.start));
_752.lastPos=node.start;
}
if(!_753){
_754.concat(" ");
}
if(!st.receiverLevel){
st.receiverLevel=0;
}
if(_755){
_754.concat("@[");
}else{
if(!_756){
if(_752.options.inlineMsgSendFunctions){
_754.concat("(___r",node);
_754.concat(++st.receiverLevel+"");
_754.concat(" = (CPArray.isa.method_msgSend[\"alloc\"] || _objj_forward)(CPArray, \"alloc\"), ___r");
_754.concat(st.receiverLevel+"");
_754.concat(" == null ? null : (___r");
_754.concat(st.receiverLevel+"");
_754.concat(".isa.method_msgSend[\"init\"] || _objj_forward)(___r");
_754.concat(st.receiverLevel+"");
_754.concat(", \"init\"))");
}else{
_754.concat("(___r");
_754.concat(++st.receiverLevel+"");
_754.concat(" = CPArray.isa.objj_msgSend0(CPArray, \"alloc\"), ___r");
_754.concat(st.receiverLevel+"");
_754.concat(" == null ? null : ___r");
_754.concat(st.receiverLevel+"");
_754.concat(".isa.objj_msgSend0(___r");
_754.concat(st.receiverLevel+"");
_754.concat(", \"init\"))");
}
if(!(st.maxReceiverLevel>=st.receiverLevel)){
st.maxReceiverLevel=st.receiverLevel;
}
}else{
if(_752.options.inlineMsgSendFunctions){
_754.concat("(___r",node);
_754.concat(++st.receiverLevel+"");
_754.concat(" = (CPArray.isa.method_msgSend[\"alloc\"] || _objj_forward)(CPArray, \"alloc\"), ___r");
_754.concat(st.receiverLevel+"");
_754.concat(" == null ? null : (___r");
_754.concat(st.receiverLevel+"");
_754.concat(".isa.method_msgSend[\"initWithObjects:count:\"] || _objj_forward)(___r");
_754.concat(st.receiverLevel+"");
_754.concat(", \"initWithObjects:count:\", [");
}else{
_754.concat("(___r",node);
_754.concat(++st.receiverLevel+"");
_754.concat(" = CPArray.isa.objj_msgSend0(CPArray, \"alloc\"), ___r");
_754.concat(st.receiverLevel+"");
_754.concat(" == null ? null : ___r");
_754.concat(st.receiverLevel+"");
_754.concat(".isa.objj_msgSend2(___r");
_754.concat(st.receiverLevel+"");
_754.concat(", \"initWithObjects:count:\", [");
}
if(!(st.maxReceiverLevel>=st.receiverLevel)){
st.maxReceiverLevel=st.receiverLevel;
}
}
}
if(_756){
for(var i=0;i<_756;i++){
var elt=node.elements[i];
if(i){
_754.concat(", ");
}
if(!_753){
_752.lastPos=elt.start;
}
c(elt,st,"Expression");
if(!_753){
_754.concat(_752.source.substring(_752.lastPos,elt.end));
}
}
if(!_755){
_754.concat("], "+_756+"))");
}
}
if(_755){
_754.concat("]");
}else{
st.receiverLevel--;
}
if(!_753){
_752.lastPos=node.end;
}
},DictionaryLiteral:function(node,st,c){
var _757=st.compiler,_758=_757.generate,_759=_757.jsBuffer,_75a=_757.options.generateObjJ,_75b=node.keys.length;
if(!_758){
_759.concat(_757.source.substring(_757.lastPos,node.start));
_757.lastPos=node.start;
}
if(!_758){
_759.concat(" ");
}
if(!st.receiverLevel){
st.receiverLevel=0;
}
if(_75a){
_759.concat("@{");
for(var i=0;i<_75b;i++){
if(i!==0){
_759.concat(",");
}
c(node.keys[i],st,"Expression");
_759.concat(":");
c(node.values[i],st,"Expression");
}
_759.concat("}");
}else{
if(!_75b){
if(_757.options.inlineMsgSendFunctions){
_759.concat("(___r",node);
_759.concat(++st.receiverLevel+"");
_759.concat(" = (CPDictionary.isa.method_msgSend[\"alloc\"] || _objj_forward)(CPDictionary, \"alloc\"), ___r");
_759.concat(st.receiverLevel+"");
_759.concat(" == null ? null : (___r");
_759.concat(st.receiverLevel+"");
_759.concat(".isa.method_msgSend[\"init\"] || _objj_forward)(___r");
_759.concat(st.receiverLevel+"");
_759.concat(", \"init\"))");
}else{
_759.concat("(___r");
_759.concat(++st.receiverLevel+"");
_759.concat(" = CPDictionary.isa.objj_msgSend0(CPDictionary, \"alloc\"), ___r");
_759.concat(st.receiverLevel+"");
_759.concat(" == null ? null : ___r");
_759.concat(st.receiverLevel+"");
_759.concat(".isa.objj_msgSend0(___r");
_759.concat(st.receiverLevel+"");
_759.concat(", \"init\"))");
}
if(!(st.maxReceiverLevel>=st.receiverLevel)){
st.maxReceiverLevel=st.receiverLevel;
}
}else{
if(_757.options.inlineMsgSendFunctions){
_759.concat("(___r",node);
_759.concat(++st.receiverLevel+"");
_759.concat(" = (CPDictionary.isa.method_msgSend[\"alloc\"] || _objj_forward)(CPDictionary, \"alloc\"), ___r");
_759.concat(st.receiverLevel+"");
_759.concat(" == null ? null : (___r");
_759.concat(st.receiverLevel+"");
_759.concat(".isa.method_msgSend[\"initWithObjects:forKeys:\"] || _objj_forward)(___r");
_759.concat(st.receiverLevel+"");
_759.concat(", \"initWithObjects:forKeys:\", [");
}else{
_759.concat("(___r",node);
_759.concat(++st.receiverLevel+"");
_759.concat(" = CPDictionary.isa.objj_msgSend0(CPDictionary, \"alloc\"), ___r");
_759.concat(st.receiverLevel+"");
_759.concat(" == null ? null : ___r");
_759.concat(st.receiverLevel+"");
_759.concat(".isa.objj_msgSend2(___r");
_759.concat(st.receiverLevel+"");
_759.concat(", \"initWithObjects:forKeys:\", [");
}
if(!(st.maxReceiverLevel>=st.receiverLevel)){
st.maxReceiverLevel=st.receiverLevel;
}
for(var i=0;i<_75b;i++){
var _75c=node.values[i];
if(i){
_759.concat(", ");
}
if(!_758){
_757.lastPos=_75c.start;
}
c(_75c,st,"Expression");
if(!_758){
_759.concat(_757.source.substring(_757.lastPos,_75c.end));
}
}
_759.concat("], [");
for(var i=0;i<_75b;i++){
var key=node.keys[i];
if(i){
_759.concat(", ");
}
if(!_758){
_757.lastPos=key.start;
}
c(key,st,"Expression");
if(!_758){
_759.concat(_757.source.substring(_757.lastPos,key.end));
}
}
_759.concat("]))");
}
}
if(!_75a){
st.receiverLevel--;
}
if(!_758){
_757.lastPos=node.end;
}
},ImportStatement:function(node,st,c){
var _75d=st.compiler,_75e=_75d.generate,_75f=_75d.jsBuffer,_760=node.localfilepath,_761=_75d.options.generateObjJ;
if(!_75e){
_75f.concat(_75d.source.substring(_75d.lastPos,node.start));
}
if(_761){
_75f.concat("@import ");
_75f.concat(_760?"\"":"<");
_75f.concat(node.filename.value);
_75f.concat(_760?"\"":">");
}else{
_75f.concat("objj_executeFile(\"",node);
_75f.concat(node.filename.value);
_75f.concat(_760?"\", YES);":"\", NO);");
}
if(!_75e){
_75d.lastPos=node.end;
}
},ClassDeclarationStatement:function(node,st,c,_762){
var _763=st.compiler,_764=_763.generate,_765=_763.jsBuffer,_766=node.classname.name,_767=_763.getClassDef(_766),_768=new _5dd(st),_769=node.type==="InterfaceDeclarationStatement",_76a=node.protocols,_76b=_763.options,_76c=_76b.generateObjJ;
_763.imBuffer=new _2f7(_763.createSourceMap,_763.URL,_76b.sourceMap&&_76b.sourceMapIncludeSource?_763.source:null);
_763.cmBuffer=new _2f7(_763.createSourceMap,_763.URL);
_763.classBodyBuffer=new _2f7(_763.createSourceMap,_763.URL);
if(_763.getTypeDef(_766)){
throw _763.error_message(_766+" is already declared as a type",node.classname);
}
if(!_764){
_765.concat(_763.source.substring(_763.lastPos,node.start));
}
if(node.superclassname){
if(_767&&_767.ivars){
throw _763.error_message("Duplicate class "+_766,node.classname);
}
if(_769&&_767&&_767.instanceMethods&&_767.classMethods){
throw _763.error_message("Duplicate interface definition for class "+_766,node.classname);
}
var _76d=_763.getClassDef(node.superclassname.name);
if(!_76d){
var _76e="Can't find superclass "+node.superclassname.name;
if(_653.importStack){
for(var i=_653.importStack.length;--i>=0;){
_76e+="\n"+(Array((_653.importStack.length-i)*2+1)).join(" ")+"Imported by: "+_653.importStack[i];
}
}
throw _763.error_message(_76e,node.superclassname);
}
_767=new _616(!_769,_766,_76d,Object.create(null));
if(!_76c){
_765.concat("\n{var the_class = objj_allocateClassPair("+node.superclassname.name+", \""+_766+"\"),\nmeta_class = the_class.isa;",node);
}
}else{
if(node.categoryname){
_767=_763.getClassDef(_766);
if(!_767){
throw _763.error_message("Class "+_766+" not found ",node.classname);
}
if(!_76c){
_765.concat("{\nvar the_class = objj_getClass(\""+_766+"\")\n",node);
_765.concat("if(!the_class) throw new SyntaxError(\"*** Could not find definition for class \\\""+_766+"\\\"\");\n");
_765.concat("var meta_class = the_class.isa;");
}
}else{
_767=new _616(!_769,_766,null,Object.create(null));
if(!_76c){
_765.concat("{var the_class = objj_allocateClassPair(Nil, \""+_766+"\"),\nmeta_class = the_class.isa;",node);
}
}
}
if(_76c){
_765.concat(_769?"@interface ":"@implementation ");
_765.concat(_766);
if(node.superclassname){
_765.concat(" : ");
c(node.superclassname,st,"IdentifierName");
}else{
if(node.categoryname){
_765.concat(" (");
c(node.categoryname,st,"IdentifierName");
_765.concat(")");
}
}
}
if(_76a){
for(var i=0,size=_76a.length;i<size;i++){
if(_76c){
if(i){
_765.concat(", ");
}else{
_765.concat(" <");
}
c(_76a[i],st,"IdentifierName");
if(i===size-1){
_765.concat(">");
}
}else{
_765.concat("\nvar aProtocol = objj_getProtocol(\""+_76a[i].name+"\");",_76a[i]);
_765.concat("\nif (!aProtocol) throw new SyntaxError(\"*** Could not find definition for protocol \\\""+_76a[i].name+"\\\"\");");
_765.concat("\nclass_addProtocol(the_class, aProtocol);");
}
}
}
_768.classDef=_767;
_763.currentSuperClass="objj_getClass(\""+_766+"\").super_class";
_763.currentSuperMetaClass="objj_getMetaClass(\""+_766+"\").super_class";
var _76f=true,_770=_767.ivars,_771=[],_772=false;
if(node.ivardeclarations){
if(_76c){
_765.concat("{");
_610+=_6b4;
}
for(var i=0;i<node.ivardeclarations.length;++i){
var _773=node.ivardeclarations[i],_774=_773.ivartype?_773.ivartype.name:null,_775=_773.ivartype?_773.ivartype.typeisclass:false,_776=_773.id,_777=_776.name,ivar={"type":_774,"name":_777},_778=_773.accessors;
var _779=function(_77a,_77b){
if(_77a.ivars[_777]){
throw _763.error_message("Instance variable '"+_777+"' is already declared for class "+_766+(_77a.name!==_766?" in superclass "+_77a.name:""),_773.id);
}
if(_77a.superClass){
_77b(_77a.superClass,_77b);
}
};
_779(_767,_779);
var _77c=!_775||typeof _1[_774]!=="undefined"||typeof window[_774]!=="undefined"||_763.getClassDef(_774)||_763.getTypeDef(_774)||_774==_767.name;
if(!_77c){
_763.addWarning(_600("Unknown type '"+_774+"' for ivar '"+_777+"'",_773.ivartype,_763.source));
}
if(_76c){
c(_773,st,"IvarDeclaration");
}else{
if(_76f){
_76f=false;
_765.concat("class_addIvars(the_class, [");
}else{
_765.concat(", ");
}
if(_76b.includeIvarTypeSignatures){
_765.concat("new objj_ivar(\""+_777+"\", \""+_774+"\")",node);
}else{
_765.concat("new objj_ivar(\""+_777+"\")",node);
}
}
if(_773.outlet){
ivar.outlet=true;
}
_771.push(ivar);
if(!_768.ivars){
_768.ivars=Object.create(null);
}
_768.ivars[_777]={type:"ivar",name:_777,node:_776,ivar:ivar};
if(_778){
var _77d=_778.property&&_778.property.name||_777,_77e=_778.getter&&_778.getter.name||_77d;
_767.addInstanceMethod(new _648(_77e,[_774]));
if(!_778.readonly){
var _77f=_778.setter?_778.setter.name:null;
if(!_77f){
var _780=_77d.charAt(0)=="_"?1:0;
_77f=(_780?"_":"")+"set"+(_77d.substr(_780,1)).toUpperCase()+_77d.substring(_780+1)+":";
}
_767.addInstanceMethod(new _648(_77f,["void",_774]));
}
_772=true;
}
}
}
if(_76c){
_610=_610.substring(_613);
_765.concatFormat("\n}");
}else{
if(!_76f){
_765.concat("]);");
}
}
if(!_76c&&!_769&&_772){
var _781=new _2f7(false);
_781.concat((_763.source.substring(node.start,node.endOfIvars)).replace(/<.*>/g,""));
_781.concat("\n");
for(var i=0;i<node.ivardeclarations.length;++i){
var _773=node.ivardeclarations[i],_774=_773.ivartype?_773.ivartype.name:null,_777=_773.id.name,_778=_773.accessors;
if(!_778){
continue;
}
var _77d=_778.property&&_778.property.name||_777,_77e=_778.getter&&_778.getter.name||_77d,_782="- ("+(_774?_774:"id")+")"+_77e+"\n{\n    return "+_777+";\n}\n";
_781.concat(_782);
if(_778.readonly){
continue;
}
var _77f=_778.setter?_778.setter.name:null;
if(!_77f){
var _780=_77d.charAt(0)=="_"?1:0;
_77f=(_780?"_":"")+"set"+(_77d.substr(_780,1)).toUpperCase()+_77d.substring(_780+1)+":";
}
var _783="- (void)"+_77f+"("+(_774?_774:"id")+")newValue\n{\n    ";
if(_778.copy){
_783+="if ("+_777+" !== newValue)\n        "+_777+" = [newValue copy];\n}\n";
}else{
_783+=_777+" = newValue;\n}\n";
}
_781.concat(_783);
}
_781.concat("\n@end");
var b=(_781.toString()).replace(/@accessors(\(.*\))?/g,"");
var _784=_64f(_76b);
_784.sourceMapIncludeSource=true;
var url=_763.url;
var _785=url&&_763.URL.substr(_763.URL.lastIndexOf("/")+1);
var _786=_785&&_785.lastIndexOf(".");
var _787=_785&&_785.substr(0,_786===-1?_785.length:_786);
var _788=_785&&_785.substr(_786===-1?_785.length:_786);
var _789=node.categoryname&&node.categoryname.id;
var _78a=_5da.compileToIMBuffer(b,_787+"_"+_766+(_789?"_"+_789:"")+"_Accessors"+(_788||""),_784);
var _78b=_78a.toString();
if(_763.createSourceMap){
_763.imBuffer.concat(_5dc.SourceNode.fromStringWithSourceMap(_78b.code,_5dc.SourceMapConsumer(_78b.map.toString())));
}else{
_763.imBuffer.concat(_78b);
}
}
for(var _78c=_771.length,i=0;i<_78c;i++){
var ivar=_771[i],_777=ivar.name;
_770[_777]=ivar;
}
_763.classDefs[_766]=_767;
var _78d=node.body,_78e=_78d.length;
if(_78e>0){
if(!_764){
_763.lastPos=_78d[0].start;
}
for(var i=0;i<_78e;++i){
var body=_78d[i];
c(body,_768,"Statement");
}
if(!_764){
_765.concat(_763.source.substring(_763.lastPos,body.end));
}
}
if(!_76c&&!_769&&!node.categoryname){
_765.concat("objj_registerClassPair(the_class);\n");
}
if(!_76c&&_763.imBuffer.isEmpty()){
_765.concat("class_addMethods(the_class, [");
_765.appendStringBuffer(_763.imBuffer);
_765.concat("]);\n");
}
if(!_76c&&_763.cmBuffer.isEmpty()){
_765.concat("class_addMethods(meta_class, [");
_765.appendStringBuffer(_763.cmBuffer);
_765.concat("]);\n");
}
if(!_76c){
_765.concat("}\n");
}
_763.jsBuffer=_765;
if(!_764){
_763.lastPos=node.end;
}
if(_76c){
_765.concat("\n@end");
}
if(_76a){
var _78f=[];
for(var i=0,size=_76a.length;i<size;i++){
var _790=_76a[i],_791=_763.getProtocolDef(_790.name);
if(!_791){
throw _763.error_message("Cannot find protocol declaration for '"+_790.name+"'",_790);
}
_78f.push(_791);
}
var _792=_767.listOfNotImplementedMethodsForProtocols(_78f);
if(_792&&_792.length>0){
for(var j=0,_793=_792.length;j<_793;j++){
var _794=_792[j],_795=_794.methodDef,_791=_794.protocolDef;
_763.addWarning(_600("Method '"+_795.name+"' in protocol '"+_791.name+"' is not implemented",node.classname,_763.source));
}
}
}
},ProtocolDeclarationStatement:function(node,st,c){
var _796=st.compiler,_797=_796.generate,_798=_796.jsBuffer,_799=node.protocolname.name,_79a=_796.getProtocolDef(_799),_79b=node.protocols,_79c=new _5dd(st),_79d=[],_79e=_796.options.generateObjJ;
if(_79a){
throw _796.error_message("Duplicate protocol "+_799,node.protocolname);
}
_796.imBuffer=new _2f7(_796.createSourceMap,_796.URL);
_796.cmBuffer=new _2f7(_796.createSourceMap,_796.URL);
if(!_797){
_798.concat(_796.source.substring(_796.lastPos,node.start));
}
if(_79e){
_798.concat("@protocol ");
c(node.protocolname,st,"IdentifierName");
}else{
_798.concat("{var the_protocol = objj_allocateProtocol(\""+_799+"\");",node);
}
if(_79b){
if(_79e){
_798.concat(" <");
}
for(var i=0,size=_79b.length;i<size;i++){
var _79f=_79b[i],_7a0=_79f.name,_7a1=_796.getProtocolDef(_7a0);
if(!_7a1){
throw _796.error_message("Can't find protocol "+_7a0,_79f);
}
if(_79e){
if(i){
_798.concat(", ");
}
c(_79f,st,"IdentifierName");
}else{
_798.concat("\nvar aProtocol = objj_getProtocol(\""+_7a0+"\");",node);
_798.concat("\nif (!aProtocol) throw new SyntaxError(\"*** Could not find definition for protocol \\\""+_799+"\\\"\");",node);
_798.concat("\nprotocol_addProtocol(the_protocol, aProtocol);",node);
}
_79d.push(_7a1);
}
if(_79e){
_798.concat(">");
}
}
_79a=new _639(_799,_79d);
_796.protocolDefs[_799]=_79a;
_79c.protocolDef=_79a;
var _7a2=node.required;
if(_7a2){
var _7a3=_7a2.length;
if(_7a3>0){
for(var i=0;i<_7a3;++i){
var _7a4=_7a2[i];
if(!_797){
_796.lastPos=_7a4.start;
}
c(_7a4,_79c,"Statement");
}
if(!_797){
_798.concat(_796.source.substring(_796.lastPos,_7a4.end));
}
}
}
if(_79e){
_798.concatFormat("\n@end");
}else{
_798.concat("\nobjj_registerProtocol(the_protocol);\n");
if(_796.imBuffer.isEmpty()){
_798.concat("protocol_addMethodDescriptions(the_protocol, [");
_798.appendStringBuffer(_796.imBuffer);
_798.concat("], true, true);\n");
}
if(_796.cmBuffer.isEmpty()){
_798.concat("protocol_addMethodDescriptions(the_protocol, [");
_798.appendStringBuffer(_796.cmBuffer);
_798.concat("], true, false);\n");
}
_798.concat("}");
}
_796.jsBuffer=_798;
if(!_797){
_796.lastPos=node.end;
}
},IvarDeclaration:function(node,st,c,_7a5){
var _7a6=st.compiler,_7a7=_7a6.jsBuffer;
if(node.outlet){
_7a7.concat("@outlet ");
}
c(node.ivartype,st,"IdentifierName");
_7a7.concat(" ");
c(node.id,st,"IdentifierName");
if(node.accessors){
_7a7.concat(" @accessors");
}
},MethodDeclarationStatement:function(node,st,c){
var _7a8=st.compiler,_7a9=_7a8.generate,_7aa=_7a8.jsBuffer,_7ab=new _5dd(st),_7ac=node.methodtype==="-",_7ad=node.selectors,_7ae=node.arguments,_7af=node.returntype,_7b0=[_7af?_7af.name:node.action?"void":"id"],_7b1=_7af?_7af.protocols:null,_7b2=_7ad[0].name,_7b3=_7a8.options.generateObjJ;
if(_7b1){
for(var i=0,size=_7b1.length;i<size;i++){
var _7b4=_7b1[i];
if(!_7a8.getProtocolDef(_7b4.name)){
_7a8.addWarning(_600("Cannot find protocol declaration for '"+_7b4.name+"'",_7b4,_7a8.source));
}
}
}
if(!_7a9){
_7aa.concat(_7a8.source.substring(_7a8.lastPos,node.start));
}
if(_7b3){
_7a8.jsBuffer.concat(_7ac?"- (":"+ (");
_7a8.jsBuffer.concat(_7b0[0]);
_7a8.jsBuffer.concat(")");
}else{
_7a8.jsBuffer=_7ac?_7a8.imBuffer:_7a8.cmBuffer;
}
var size=_7ae.length;
if(size>0){
for(var i=0;i<_7ae.length;i++){
var _7b5=_7ae[i],_7b6=_7b5.type,_7b7=_7b6?_7b6.name:"id",_7b8=_7b6?_7b6.protocols:null;
_7b0.push(_7b7);
if(i===0){
_7b2+=":";
}else{
_7b2+=(_7ad[i]?_7ad[i].name:"")+":";
}
if(_7b8){
for(var j=0,size=_7b8.length;j<size;j++){
var _7b9=_7b8[j];
if(!_7a8.getProtocolDef(_7b9.name)){
_7a8.addWarning(_600("Cannot find protocol declaration for '"+_7b9.name+"'",_7b9,_7a8.source));
}
}
}
if(_7b3){
var _7ba=_7ad[i];
if(i){
_7a8.jsBuffer.concat(" ");
}
_7a8.jsBuffer.concat((_7ba?_7ba.name:"")+":");
_7a8.jsBuffer.concat("(");
_7a8.jsBuffer.concat(_7b7);
if(_7b8){
_7a8.jsBuffer.concat(" <");
for(var j=0,size=_7b8.length;j<size;j++){
var _7b9=_7b8[j];
if(j){
_7a8.jsBuffer.concat(", ");
}
_7a8.jsBuffer.concat(_7b9.name);
}
_7a8.jsBuffer.concat(">");
}
_7a8.jsBuffer.concat(")");
c(_7b5.identifier,st,"IdentifierName");
}
}
}else{
if(_7b3){
var _7bb=_7ad[0];
_7a8.jsBuffer.concat(_7bb.name,_7bb);
}
}
if(_7b3){
if(node.parameters){
_7a8.jsBuffer.concat(", ...");
}
}else{
if(_7a8.jsBuffer.isEmpty()){
_7a8.jsBuffer.concat(", ");
}
_7a8.jsBuffer.concat("new objj_method(sel_getUid(\"",node);
_7a8.jsBuffer.concat(_7b2);
_7a8.jsBuffer.concat("\"), ");
}
if(node.body){
if(!_7b3){
_7a8.jsBuffer.concat("function");
if(_7a8.options.includeMethodFunctionNames){
_7a8.jsBuffer.concat(" $"+st.currentClassName()+"__"+_7b2.replace(/:/g,"_"));
}
_7a8.jsBuffer.concat("(self, _cmd");
}
_7ab.methodType=node.methodtype;
_7ab.vars["self"]={type:"method base",scope:_7ab};
_7ab.vars["_cmd"]={type:"method base",scope:_7ab};
if(_7ae){
for(var i=0;i<_7ae.length;i++){
var _7b5=_7ae[i],_7bc=_7b5.identifier.name;
if(!_7b3){
_7a8.jsBuffer.concat(", ");
_7a8.jsBuffer.concat(_7bc,_7b5.identifier);
}
_7ab.vars[_7bc]={type:"method argument",node:_7b5};
}
}
if(!_7b3){
_7a8.jsBuffer.concat(")\n");
}
if(!_7a9){
_7a8.lastPos=node.startOfBody;
}
_610+=_6b4;
_7ab.endOfScopeBody=true;
c(node.body,_7ab,"Statement");
_610=_610.substring(_613);
if(!_7a9){
_7a8.jsBuffer.concat(_7a8.source.substring(_7a8.lastPos,node.body.end));
}
if(!_7b3){
_7a8.jsBuffer.concat("\n");
}
}else{
if(_7b3){
_7a8.jsBuffer.concat(";");
}else{
_7a8.jsBuffer.concat("Nil\n");
}
}
if(!_7b3){
if(_7a8.options.includeMethodArgumentTypeSignatures){
_7a8.jsBuffer.concat(","+JSON.stringify(_7b0));
}
_7a8.jsBuffer.concat(")");
_7a8.jsBuffer=_7aa;
}
if(!_7a9){
_7a8.lastPos=node.end;
}
var def=st.classDef,_7bd;
if(def){
_7bd=_7ac?def.getInstanceMethod(_7b2):def.getClassMethod(_7b2);
}else{
def=st.protocolDef;
}
if(!def){
throw "InternalError: MethodDeclaration without ClassDeclaration or ProtocolDeclaration at line: "+(_5db.getLineInfo(_7a8.source,node.start)).line;
}
if(!_7bd){
var _7be=def.protocols;
if(_7be){
for(var i=0,size=_7be.length;i<size;i++){
var _7bf=_7be[i],_7bd=_7ac?_7bf.getInstanceMethod(_7b2):_7bf.getClassMethod(_7b2);
if(_7bd){
break;
}
}
}
}
if(_7bd){
var _7c0=_7bd.types;
if(_7c0){
var _7c1=_7c0.length;
if(_7c1>0){
var _7c2=_7c0[0];
if(_7c2!==_7b0[0]&&!(_7c2==="id"&&_7af&&_7af.typeisclass)){
_7a8.addWarning(_600("Conflicting return type in implementation of '"+_7b2+"': '"+_7c2+"' vs '"+_7b0[0]+"'",_7af||node.action||_7ad[0],_7a8.source));
}
for(var i=1;i<_7c1;i++){
var _7c3=_7c0[i];
if(_7c3!==_7b0[i]&&!(_7c3==="id"&&_7ae[i-1].type.typeisclass)){
_7a8.addWarning(_600("Conflicting parameter types in implementation of '"+_7b2+"': '"+_7c3+"' vs '"+_7b0[i]+"'",_7ae[i-1].type||_7ae[i-1].identifier,_7a8.source));
}
}
}
}
}
var _7c4=new _648(_7b2,_7b0);
if(_7ac){
def.addInstanceMethod(_7c4);
}else{
def.addClassMethod(_7c4);
}
},MessageSendExpression:function(node,st,c){
var _7c5=st.compiler,_7c6=_7c5.generate,_7c7=_7c5.options.inlineMsgSendFunctions,_7c8=_7c5.jsBuffer,_7c9=node.object,_7ca=node.selectors,_7cb=node.arguments,_7cc=_7cb.length,_7cd=_7ca[0],_7ce=_7cd?_7cd.name:"",_7cf=node.parameters,_7d0=_7c5.options.generateObjJ;
for(var i=0;i<_7cc;i++){
if(i!==0){
var _7d1=_7ca[i];
if(_7d1){
_7ce+=_7d1.name;
}
}
_7ce+=":";
}
if(!_7c6){
_7c8.concat(_7c5.source.substring(_7c5.lastPos,node.start));
_7c5.lastPos=_7c9?_7c9.start:node.arguments.length?node.arguments[0].start:node.end;
}else{
if(!_7c7){
var _7d2=_7cc;
if(_7cf){
_7d2+=_7cf.length;
}
}
}
if(node.superObject){
if(!_7c6){
_7c8.concat(" ");
}
if(_7d0){
_7c8.concat("[super ");
}else{
if(_7c7){
_7c8.concat("(",node);
_7c8.concat(st.currentMethodType()==="+"?_7c5.currentSuperMetaClass:_7c5.currentSuperClass);
_7c8.concat(".method_dtable[\"",node);
_7c8.concat(_7ce);
_7c8.concat("\"] || _objj_forward)(self",node);
}else{
_7c8.concat("objj_msgSendSuper",node);
if(_7d2<4){
_7c8.concat(""+_7d2);
}
_7c8.concat("({ receiver:self, super_class:"+(st.currentMethodType()==="+"?_7c5.currentSuperMetaClass:_7c5.currentSuperClass)+" }",node);
}
}
}else{
if(_7c6){
var _7d3=_7c9.type==="Identifier"&&!(st.currentMethodType()==="-"&&_7c5.getIvarForClass(_7c9.name,st)&&!st.getLvar(_7c9.name,true)),_7d4,_7d5;
if(_7d3){
var name=_7c9.name,_7d4=st.getLvar(name);
if(name==="self"){
_7d5=!_7d4||!_7d4.scope||_7d4.scope.assignmentToSelf;
}else{
_7d5=!!_7d4||!_7c5.getClassDef(name);
}
if(_7d5){
_7c8.concat("(",node);
c(_7c9,st,"Expression");
_7c8.concat(" == null ? null : ",node);
}
if(_7c7){
_7c8.concat("(",node);
}
c(_7c9,st,"Expression");
}else{
_7d5=true;
if(!st.receiverLevel){
st.receiverLevel=0;
}
_7c8.concat("((___r"+ ++st.receiverLevel,node);
_7c8.concat(" = ",node);
c(_7c9,st,"Expression");
_7c8.concat(")",node);
_7c8.concat(", ___r"+st.receiverLevel,node);
_7c8.concat(" == null ? null : ",node);
if(_7c7){
_7c8.concat("(",node);
}
_7c8.concat("___r"+st.receiverLevel,node);
if(!(st.maxReceiverLevel>=st.receiverLevel)){
st.maxReceiverLevel=st.receiverLevel;
}
}
if(_7c7){
_7c8.concat(".isa.method_msgSend[\"",node);
_7c8.concat(_7ce,node);
_7c8.concat("\"] || _objj_forward)",node);
}else{
_7c8.concat(".isa.objj_msgSend",node);
}
}else{
_7c8.concat(" ");
_7c8.concat("objj_msgSend(");
_7c8.concat(_7c5.source.substring(_7c5.lastPos,_7c9.end));
}
}
if(_7d0){
for(var i=0;i<_7cc||_7cc===0&&i===0;i++){
var _7ce=_7ca[i];
_7c8.concat(" ");
_7c8.concat(_7ce?_7ce.name:"");
if(_7cc>0){
var _7d6=_7cb[i];
_7c8.concat(":");
c(_7d6,st,"Expression");
}
}
if(_7cf){
for(var i=0,size=_7cf.length;i<size;++i){
var _7d7=_7cf[i];
_7c8.concat(", ");
c(_7d7,st,"Expression");
}
}
_7c8.concat("]");
}else{
if(_7c6&&!node.superObject){
if(!_7c7){
if(_7d2<4){
_7c8.concat(""+_7d2,null);
}
}
if(_7d3){
_7c8.concat("(",node);
c(_7c9,st,"Expression");
}else{
_7c8.concat("(___r"+st.receiverLevel,node);
}
}
_7c8.concat(", \"",node);
_7c8.concat(_7ce);
_7c8.concat("\"",node);
if(_7cb){
for(var i=0;i<_7cb.length;i++){
var _7d6=_7cb[i];
_7c8.concat(", ",node);
if(!_7c6){
_7c5.lastPos=_7d6.start;
}
c(_7d6,st,"Expression");
if(!_7c6){
_7c8.concat(_7c5.source.substring(_7c5.lastPos,_7d6.end));
_7c5.lastPos=_7d6.end;
}
}
}
if(_7cf){
for(var i=0;i<_7cf.length;++i){
var _7d7=_7cf[i];
_7c8.concat(", ",node);
if(!_7c6){
_7c5.lastPos=_7d7.start;
}
c(_7d7,st,"Expression");
if(!_7c6){
_7c8.concat(_7c5.source.substring(_7c5.lastPos,_7d7.end));
_7c5.lastPos=_7d7.end;
}
}
}
if(_7c6&&!node.superObject){
if(_7d5){
_7c8.concat(")",node);
}
if(!_7d3){
st.receiverLevel--;
}
}
_7c8.concat(")",node);
}
if(!_7c6){
_7c5.lastPos=node.end;
}
},SelectorLiteralExpression:function(node,st,c){
var _7d8=st.compiler,_7d9=_7d8.jsBuffer,_7da=_7d8.generate,_7db=_7d8.options.generateObjJ;
if(!_7da){
_7d9.concat(_7d8.source.substring(_7d8.lastPos,node.start));
_7d9.concat(" ");
}
_7d9.concat(_7db?"@selector(":"sel_getUid(\"",node);
_7d9.concat(node.selector);
_7d9.concat(_7db?")":"\")");
if(!_7da){
_7d8.lastPos=node.end;
}
},ProtocolLiteralExpression:function(node,st,c){
var _7dc=st.compiler,_7dd=_7dc.jsBuffer,_7de=_7dc.generate,_7df=_7dc.options.generateObjJ;
if(!_7de){
_7dd.concat(_7dc.source.substring(_7dc.lastPos,node.start));
_7dd.concat(" ");
}
_7dd.concat(_7df?"@protocol(":"objj_getProtocol(\"",node);
c(node.id,st,"IdentifierName");
_7dd.concat(_7df?")":"\")");
if(!_7de){
_7dc.lastPos=node.end;
}
},Reference:function(node,st,c){
var _7e0=st.compiler,_7e1=_7e0.jsBuffer,_7e2=_7e0.generate,_7e3=_7e0.options.generateObjJ;
if(!_7e2){
_7e1.concat(_7e0.source.substring(_7e0.lastPos,node.start));
_7e1.concat(" ");
}
if(_7e3){
_7e1.concat("@ref(",node);
_7e1.concat(node.element.name,node.element);
_7e1.concat(")",node);
}else{
_7e1.concat("function(__input) { if (arguments.length) return ",node);
c(node.element,st,"Expression");
_7e1.concat(" = __input; return ");
c(node.element,st,"Expression");
_7e1.concat("; }");
}
if(!_7e2){
_7e0.lastPos=node.end;
}
},Dereference:function(node,st,c){
var _7e4=st.compiler,_7e5=_7e4.jsBuffer,_7e6=_7e4.generate,_7e7=_7e4.options.generateObjJ;
_6a6(st,node.expr);
if(!_7e6){
_7e5.concat(_7e4.source.substring(_7e4.lastPos,node.start));
_7e4.lastPos=node.expr.start;
}
if(_7e7){
_7e5.concat("@deref(");
}
c(node.expr,st,"Expression");
if(!_7e6){
_7e5.concat(_7e4.source.substring(_7e4.lastPos,node.expr.end));
}
if(_7e7){
_7e5.concat(")");
}else{
_7e5.concat("()");
}
if(!_7e6){
_7e4.lastPos=node.end;
}
},ClassStatement:function(node,st,c){
var _7e8=st.compiler,_7e9=_7e8.jsBuffer,_7ea=_7e8.options.generateObjJ;
if(!_7e8.generate){
_7e9.concat(_7e8.source.substring(_7e8.lastPos,node.start));
_7e8.lastPos=node.start;
_7e9.concat("//");
}
if(_7ea){
_7e9.concat("@class ");
c(node.id,st,"IdentifierName");
}
var _7eb=node.id.name;
if(_7e8.getTypeDef(_7eb)){
throw _7e8.error_message(_7eb+" is already declared as a type",node.id);
}
if(!_7e8.getClassDef(_7eb)){
_7e8.classDefs[_7eb]=new _616(false,_7eb);
}
st.vars[node.id.name]={type:"class",node:node.id};
},GlobalStatement:function(node,st,c){
var _7ec=st.compiler,_7ed=_7ec.jsBuffer,_7ee=_7ec.options.generateObjJ;
if(!_7ec.generate){
_7ed.concat(_7ec.source.substring(_7ec.lastPos,node.start));
_7ec.lastPos=node.start;
_7ed.concat("//");
}
if(_7ee){
_7ed.concat("@global ");
c(node.id,st,"IdentifierName");
}
(st.rootScope()).vars[node.id.name]={type:"global",node:node.id};
},PreprocessStatement:function(node,st,c){
var _7ef=st.compiler;
if(!_7ef.generate){
_7ef.jsBuffer.concat(_7ef.source.substring(_7ef.lastPos,node.start));
_7ef.lastPos=node.start;
_7ef.jsBuffer.concat("//");
}
},TypeDefStatement:function(node,st,c){
var _7f0=st.compiler,_7f1=_7f0.generate,_7f2=_7f0.jsBuffer,_7f3=node.typedefname.name,_7f4=_7f0.getTypeDef(_7f3),_7f5=new _5dd(st);
if(_7f4){
throw _7f0.error_message("Duplicate type definition "+_7f3,node.typedefname);
}
if(_7f0.getClassDef(_7f3)){
throw _7f0.error_message(_7f3+" is already declared as class",node.typedefname);
}
if(!_7f1){
_7f2.concat(_7f0.source.substring(_7f0.lastPos,node.start));
}
_7f2.concat("{var the_typedef = objj_allocateTypeDef(\""+_7f3+"\");",node);
_7f4=new _647(_7f3);
_7f0.typeDefs[_7f3]=_7f4;
_7f5.typeDef=_7f4;
_7f2.concat("\nobjj_registerTypeDef(the_typedef);\n");
_7f2.concat("}");
if(!_7f1){
_7f0.lastPos=node.end;
}
}});
});
function _335(aURL,_7f6){
this._URL=aURL;
this._isLocal=_7f6;
};
_2.FileDependency=_335;
_335.prototype.URL=function(){
return this._URL;
};
_335.prototype.isLocal=function(){
return this._isLocal;
};
_335.prototype.toMarkedString=function(){
var _7f7=(this.URL()).absoluteString();
return (this.isLocal()?_266:_265)+";"+_7f7.length+";"+_7f7;
};
_335.prototype.toString=function(){
return (this.isLocal()?"LOCAL: ":"STD: ")+this.URL();
};
var _7f8=0,_7f9=1,_7fa=2,_7fb=3,_7fc=0;
function _306(_7fd,_7fe,aURL,_7ff,_800,_801){
if(arguments.length===0){
return this;
}
this._code=_7fd;
this._function=_7ff||null;
this._URL=_1e4(aURL||new CFURL("(Anonymous"+_7fc++ +")"));
this._compiler=_800||null;
this._fileDependencies=_7fe;
this._filenameTranslateDictionary=_801;
if(!_7fe){
this._fileDependencyStatus=_7fb;
this._fileDependencyCallbacks=[];
}else{
if(_7fe.length){
this._fileDependencyStatus=_7f8;
this._fileDependencyCallbacks=[];
}else{
this._fileDependencyStatus=_7fa;
}
}
if(this._function){
return;
}
if(!_800){
this.setCode(_7fd);
}
};
_2.Executable=_306;
_306.prototype.path=function(){
return (this.URL()).path();
};
_306.prototype.URL=function(){
return this._URL;
};
_306.prototype.functionParameters=function(){
var _802=["global","objj_executeFile","objj_importFile"];
return _802;
};
_306.prototype.functionArguments=function(){
var _803=[_1,this.fileExecuter(),this.fileImporter()];
return _803;
};
_306.prototype.execute=function(){
if(this._compiler){
var _804=this.fileDependencies(),_a0=0,_805=_804.length;
this._compiler.pushImport((this.URL()).lastPathComponent());
for(;_a0<_805;++_a0){
var _806=_804[_a0],_807=_806.isLocal(),URL=_806.URL();
this.fileExecuter()(URL,_807);
}
this._compiler.popImport();
this.setCode(this._compiler.compilePass2(),this._compiler.map());
if(_808.printWarningsAndErrors(this._compiler,_2.messageOutputFormatInXML)){
throw "Compilation error";
}
this._compiler=null;
}
var _809=_80a;
_80a=CFBundle.bundleContainingURL(this.URL());
var _80b=this._function.apply(_1,this.functionArguments());
_80a=_809;
return _80b;
};
_306.prototype.code=function(){
return this._code;
};
_306.prototype.setCode=function(code,_80c){
this._code=code;
var _80d=(this.functionParameters()).join(",");
this._function=new Function(_80d,code);
};
_306.prototype.fileDependencies=function(){
return this._fileDependencies;
};
_306.prototype.setFileDependencies=function(_80e){
this._fileDependencies=_80e;
};
_306.prototype.hasLoadedFileDependencies=function(){
return this._fileDependencyStatus===_7fa;
};
var _80f=0,_810=[],_811={};
_306.prototype.loadFileDependencies=function(_812){
var _813=this._fileDependencyStatus;
if(_812){
if(_813===_7fa){
return _812();
}
this._fileDependencyCallbacks.push(_812);
}
if(_813===_7f8){
if(_80f){
throw "Can't load";
}
_814(this);
}
};
_306.prototype.setExecutableUnloadedFileDependencies=function(){
if(this._fileDependencyStatus===_7fb){
this._fileDependencyStatus=_7f8;
}
};
_306.prototype.isExecutableCantStartLoadYetFileDependencies=function(){
return this._fileDependencyStatus===_7fb;
};
function _814(_815){
_810.push(_815);
_815._fileDependencyStatus=_7f9;
var _816=_815.fileDependencies(),_a0=0,_817=_816.length,_818=_815.referenceURL(),_819=_818.absoluteString(),_81a=_815.fileExecutableSearcher();
_80f+=_817;
for(;_a0<_817;++_a0){
var _81b=_816[_a0],_81c=_81b.isLocal(),URL=_81b.URL(),_81d=(_81c&&_819+" "||"")+URL;
if(_811[_81d]){
if(--_80f===0){
_81e();
}
continue;
}
_811[_81d]=YES;
_81a(URL,_81c,_81f);
}
};
function _81f(_820){
--_80f;
if(_820._fileDependencyStatus===_7f8){
_814(_820);
}else{
if(_80f===0){
_81e();
}
}
};
function _81e(){
var _821=_810,_a0=0,_822=_821.length;
_810=[];
for(;_a0<_822;++_a0){
_821[_a0]._fileDependencyStatus=_7fa;
}
for(_a0=0;_a0<_822;++_a0){
var _823=_821[_a0],_824=_823._fileDependencyCallbacks,_825=0,_826=_824.length;
for(;_825<_826;++_825){
_824[_825]();
}
_823._fileDependencyCallbacks=[];
}
};
_306.prototype.referenceURL=function(){
if(this._referenceURL===_32){
this._referenceURL=new CFURL(".",this.URL());
}
return this._referenceURL;
};
_306.prototype.fileImporter=function(){
return _306.fileImporterForURL(this.referenceURL());
};
_306.prototype.fileExecuter=function(){
return _306.fileExecuterForURL(this.referenceURL());
};
_306.prototype.fileExecutableSearcher=function(){
return _306.fileExecutableSearcherForURL(this.referenceURL());
};
var _827={};
_306.fileExecuterForURL=function(aURL){
var _828=_1e4(aURL),_829=_828.absoluteString(),_82a=_827[_829];
if(!_82a){
_82a=function(aURL,_82b,_82c){
_306.fileExecutableSearcherForURL(_828)(aURL,_82b,function(_82d){
if(!_82d.hasLoadedFileDependencies()){
throw "No executable loaded for file at URL "+aURL;
}
_82d.execute(_82c);
});
};
_827[_829]=_82a;
}
return _82a;
};
var _82e={};
_306.fileImporterForURL=function(aURL){
var _82f=_1e4(aURL),_830=_82f.absoluteString(),_831=_82e[_830];
if(!_831){
_831=function(aURL,_832,_833){
_17d();
_306.fileExecutableSearcherForURL(_82f)(aURL,_832,function(_834){
_834.loadFileDependencies(function(){
_834.execute();
_17e();
if(_833){
_833();
}
});
});
};
_82e[_830]=_831;
}
return _831;
};
var _835={},_836={};
function _291(x){
var _837=0;
for(var k in x){
if(x.hasOwnProperty(k)){
++_837;
}
}
return _837;
};
_306.resetCachedFileExecutableSearchers=function(){
_835={};
_836={};
_82e={};
_827={};
_811={};
};
_306.fileExecutableSearcherForURL=function(_838){
var _839=_838.absoluteString(),_83a=_835[_839];
if(!_83a){
var _83b=_306.filenameTranslateDictionary?_306.filenameTranslateDictionary():null;
_83a=function(aURL,_83c,_83d){
var _83e=(_83c&&_838||"")+aURL,_83f=_836[_83e];
if(_83f){
return _840(_83f);
}
var _841=aURL instanceof CFURL&&aURL.scheme();
if(_83c||_841){
if(!_841){
aURL=new CFURL(aURL,_838);
}
_1cd.resolveResourceAtURL(aURL,NO,_840,_83b);
}else{
_1cd.resolveResourceAtURLSearchingIncludeURLs(aURL,_840);
}
function _840(_842){
if(!_842){
var _843=_2.ObjJCompiler?_2.ObjJCompiler.currentCompileFile:null;
throw new Error("Could not load file at "+aURL+(_843?" when compiling "+_843:"")+"\nwith includeURLs: "+_1cd.includeURLs());
}
_836[_83e]=_842;
_83d(new _808(_842.URL(),_83b));
};
};
_835[_839]=_83a;
}
return _83a;
};
var _844=55296;
var _845=56319;
var _846=56320;
var _847=57343;
var _848=65533;
var _849=[0,192,224,240,248,252];
function _84a(_84b){
var _84c="";
var _84d=0;
for(var i=0;i<_84b.length;i++){
var c=_84b.charCodeAt(i);
if(c<128){
continue;
}
if(i>_84d){
_84c+=_84b.substring(_84d,i);
}
if(c>=_844&&c<=_845){
i++;
if(i<_84b.length){
var c2=_84b.charCodeAt(i);
if(c2>=_846&&c2<=_847){
c=(c-_844<<10)+(c2-_846)+65536;
}else{
return null;
}
}else{
return null;
}
}else{
if(c>=_846&&c<=_847){
return null;
}
}
_84d=i+1;
enc=[];
var cc=c;
if(cc>=1114112){
cc=2048;
c=_848;
}
if(cc>=65536){
enc.unshift(String.fromCharCode((c|128)&191));
c>>=6;
}
if(cc>=2048){
enc.unshift(String.fromCharCode((c|128)&191));
c>>=6;
}
if(cc>=128){
enc.unshift(String.fromCharCode((c|128)&191));
c>>=6;
}
enc.unshift(String.fromCharCode(c|_849[enc.length]));
_84c+=enc.join("");
}
if(_84d===0){
return _84b;
}
if(i>_84d){
_84c+=_84b.substring(_84d,i);
}
return _84c;
};
var _84e={};
var _84f={};
var _850="";
function _808(aURL,_851){
aURL=_1e4(aURL);
var _852=aURL.absoluteString(),_853=_84e[_852];
if(_853){
return _853;
}
_84e[_852]=this;
var _854=(_1cd.resourceAtURL(aURL)).contents(),_855=NULL,_856=(aURL.pathExtension()).toLowerCase();
this._hasExecuted=NO;
if(_854.match(/^@STATIC;/)){
_855=_857(_854,aURL);
}else{
if((_856==="j"||!_856)&&!_854.match(/^{/)){
var _858=_84f||{};
this.cachedIncludeFileSearchResultsContent={};
this.cachedIncludeFileSearchResultsURL={};
_859(this,_854,aURL,_858,_851);
return;
}else{
_855=new _306(_854,[],aURL);
}
}
_306.apply(this,[_855.code(),_855.fileDependencies(),aURL,_855._function,_855._compiler,_851]);
};
_2.FileExecutable=_808;
_808.prototype=new _306();
var _859=function(self,_85a,aURL,_85b,_85c){
var _85d=_85b.acornOptions||(_85b.acornOptions={});
_85d.preprocessGetIncludeFile=function(_85e,_85f){
var _860=new CFURL(".",aURL),_861=new CFURL(_85e);
var _862=(_85f&&_860||"")+_861,_863=self.cachedIncludeFileSearchResultsContent[_862];
if(!_863){
var _864=_861 instanceof CFURL&&_861.scheme(),_865=NO;
function _866(_867){
var _868=_867&&_867.contents(),_869=_868&&_868.charCodeAt(_868.length-1);
if(_868==null){
throw new Error("Can't load file "+_861);
}
if(_869!==10&&_869!==13&&_869!==8232&&_869!==8233){
_868+="\n";
}
self.cachedIncludeFileSearchResultsContent[_862]=_868;
self.cachedIncludeFileSearchResultsURL[_862]=_867.URL();
if(_865){
_859(self,_85a,aURL,_85b,_85c);
}
};
if(_85f||_864){
if(!_864){
_861=new CFURL(_861,new CFURL(_85c[aURL.lastPathComponent()]||".",_860));
}
_1cd.resolveResourceAtURL(_861,NO,_866);
}else{
_1cd.resolveResourceAtURLSearchingIncludeURLs(_861,_866);
}
_863=self.cachedIncludeFileSearchResultsContent[_862];
}
if(_863){
return {include:_863,sourceFile:self.cachedIncludeFileSearchResultsURL[_862]};
}else{
_865=YES;
return null;
}
};
var _86a=_84f&&_84f.includeFiles,_86b=true;
_85d.preIncludeFiles=[];
if(_86a){
for(var i=0,size=_86a.length;i<size;i++){
var _86c=_1e4(_86a[i]);
try{
var _86d=_1cd.resourceAtURL(_1e4(_86c));
}
catch(e){
_1cd.resolveResourcesAtURLs(_86a.map(function(u){
return _1e4(u);
}),function(){
_859(self,_85a,aURL,_85b,_85c);
});
_86b=false;
break;
}
if(_86d){
if(_86d.isNotFound()){
throw new Error("--include file not found "+includeUrl);
}
var _86e=_86d.contents();
var _86f=_86e.charCodeAt(_86e.length-1);
if(_86f!==10&&_86f!==13&&_86f!==8232&&_86f!==8233){
_86e+="\n";
}
_85d.preIncludeFiles.push({include:_86e,sourceFile:_86c.toString()});
}
}
}
if(_86b){
var _870=_2.ObjJCompiler.compileFileDependencies(_85a,aURL,_85b);
var _871=_870.warningsAndErrors;
if(_871&&_871.length===1&&_871[0].message.indexOf("file not found")>-1){
return;
}
if(_808.printWarningsAndErrors(_870,_2.messageOutputFormatInXML)){
throw "Compilation error";
}
var _872=_870.dependencies.map(function(_873){
return new _335(new CFURL(_873.url),_873.isLocal);
});
}
if(self.isExecutableCantStartLoadYetFileDependencies()){
self.setFileDependencies(_872);
self.setExecutableUnloadedFileDependencies();
self.loadFileDependencies();
}else{
if(self._fileDependencyStatus==null){
executable=new _306(_870&&_870.jsBuffer?_870.jsBuffer.toString():null,_872,aURL,null,_870);
_306.apply(self,[executable.code(),executable.fileDependencies(),aURL,executable._function,executable._compiler,_85c]);
}
}
};
_808.resetFileExecutables=function(){
_84e={};
_874={};
};
_808.prototype.execute=function(_875){
if(this._hasExecuted&&!_875){
return;
}
this._hasExecuted=YES;
_306.prototype.execute.call(this);
};
_808.prototype.hasExecuted=function(){
return this._hasExecuted;
};
function _857(_876,aURL){
var _877=new _11f(_876);
var _878=NULL,code="",_879=[];
while(_878=_877.getMarker()){
var text=_877.getString();
if(_878===_264){
code+=text;
}else{
if(_878===_265){
_879.push(new _335(new CFURL(text),NO));
}else{
if(_878===_266){
_879.push(new _335(new CFURL(text),YES));
}
}
}
}
var fn=_808._lookupCachedFunction(aURL);
if(fn){
return new _306(code,_879,aURL,fn);
}
return new _306(code,_879,aURL);
};
var _874={};
_808._cacheFunction=function(aURL,fn){
aURL=typeof aURL==="string"?aURL:aURL.absoluteString();
_874[aURL]=fn;
};
_808._lookupCachedFunction=function(aURL){
aURL=typeof aURL==="string"?aURL:aURL.absoluteString();
return _874[aURL];
};
_808.setCurrentGccCompilerFlags=function(_87a){
if(_850===_87a){
return;
}
_850=_87a;
var _87b=_2.ObjJCompiler.parseGccCompilerFlags(_87a);
_808.setCurrentCompilerFlags(_87b);
};
_808.currentGccCompilerFlags=function(_87c){
return _850;
};
_808.setCurrentCompilerFlags=function(_87d){
_84f=_87d;
if(_84f.transformNamedFunctionDeclarationToAssignment==null){
_84f.transformNamedFunctionDeclarationToAssignment=true;
}
if(_84f.sourceMap==null){
_84f.sourceMap=false;
}
if(_84f.inlineMsgSendFunctions==null){
_84f.inlineMsgSendFunctions=false;
}
};
_808.currentCompilerFlags=function(_87e){
return _84f;
};
_808.printWarningsAndErrors=function(_87f,_880){
var _881=[],_882=false;
for(var i=0;i<_87f.warningsAndErrors.length;i++){
var _883=_87f.warningsAndErrors[i],_884=_87f.prettifyMessage(_883);
_882=_882||_883.messageType==="ERROR";
console.log(_884);
}
return _882;
};
_808.setCurrentCompilerFlags({});
var _885=1,_886=2,_887=4,_888=8;
objj_ivar=function(_889,_88a){
this.name=_889;
this.type=_88a;
};
objj_method=function(_88b,_88c,_88d){
var _88e=_88c||function(_88f,_890){
CPException.isa.objj_msgSend2(CPException,"raise:reason:",CPInternalInconsistencyException,_88f.isa.method_msgSend0(self,"className")+" does not have an implementation for selector '"+_890+"'");
};
_88e.method_name=_88b;
_88e.method_imp=_88c;
_88e.method_types=_88d;
return _88e;
};
objj_class=function(_891){
this.isa=NULL;
this.version=0;
this.super_class=NULL;
this.name=NULL;
this.info=0;
this.ivar_list=[];
this.ivar_store=function(){
};
this.ivar_dtable=this.ivar_store.prototype;
this.method_list=[];
this.method_store=function(){
};
this.method_dtable=this.method_store.prototype;
this.protocol_list=[];
this.allocator=function(){
};
this._UID=-1;
};
objj_protocol=function(_892){
this.name=_892;
this.instance_methods={};
this.class_methods={};
};
objj_object=function(){
this.isa=NULL;
this._UID=-1;
};
objj_typeDef=function(_893){
this.name=_893;
};
class_getName=function(_894){
if(_894==Nil){
return "";
}
return _894.name;
};
class_isMetaClass=function(_895){
if(!_895){
return NO;
}
return _895.info&_886;
};
class_getSuperclass=function(_896){
if(_896==Nil){
return Nil;
}
return _896.super_class;
};
class_setSuperclass=function(_897,_898){
_897.super_class=_898;
_897.isa.super_class=_898.isa;
};
class_addIvar=function(_899,_89a,_89b){
var _89c=_899.allocator.prototype;
if(typeof _89c[_89a]!="undefined"){
return NO;
}
var ivar=new objj_ivar(_89a,_89b);
_899.ivar_list.push(ivar);
_899.ivar_dtable[_89a]=ivar;
_89c[_89a]=NULL;
return YES;
};
class_addIvars=function(_89d,_89e){
var _89f=0,_8a0=_89e.length,_8a1=_89d.allocator.prototype;
for(;_89f<_8a0;++_89f){
var ivar=_89e[_89f],name=ivar.name;
if(typeof _8a1[name]==="undefined"){
_89d.ivar_list.push(ivar);
_89d.ivar_dtable[name]=ivar;
_8a1[name]=NULL;
}
}
};
class_copyIvarList=function(_8a2){
return _8a2.ivar_list.slice(0);
};
class_addMethod=function(_8a3,_8a4,_8a5,_8a6){
var _8a7=new objj_method(_8a4,_8a5,_8a6);
_8a3.method_list.push(_8a7);
_8a3.method_dtable[_8a4]=_8a7;
if(!(_8a3.info&_886)&&(_8a3.info&_886?_8a3:_8a3.isa).isa===(_8a3.info&_886?_8a3:_8a3.isa)){
class_addMethod(_8a3.info&_886?_8a3:_8a3.isa,_8a4,_8a5,_8a6);
}
return YES;
};
class_addMethods=function(_8a8,_8a9){
var _8aa=0,_8ab=_8a9.length,_8ac=_8a8.method_list,_8ad=_8a8.method_dtable;
for(;_8aa<_8ab;++_8aa){
var _8ae=_8a9[_8aa];
_8ac.push(_8ae);
_8ad[_8ae.method_name]=_8ae;
}
if(!(_8a8.info&_886)&&(_8a8.info&_886?_8a8:_8a8.isa).isa===(_8a8.info&_886?_8a8:_8a8.isa)){
class_addMethods(_8a8.info&_886?_8a8:_8a8.isa,_8a9);
}
};
class_getInstanceMethod=function(_8af,_8b0){
if(!_8af||!_8b0){
return NULL;
}
var _8b1=_8af.method_dtable[_8b0];
return _8b1?_8b1:NULL;
};
class_getInstanceVariable=function(_8b2,_8b3){
if(!_8b2||!_8b3){
return NULL;
}
var _8b4=_8b2.ivar_dtable[_8b3];
return _8b4;
};
class_getClassMethod=function(_8b5,_8b6){
if(!_8b5||!_8b6){
return NULL;
}
var _8b7=(_8b5.info&_886?_8b5:_8b5.isa).method_dtable[_8b6];
return _8b7?_8b7:NULL;
};
class_respondsToSelector=function(_8b8,_8b9){
return class_getClassMethod(_8b8,_8b9)!=NULL;
};
class_copyMethodList=function(_8ba){
return _8ba.method_list.slice(0);
};
class_getVersion=function(_8bb){
return _8bb.version;
};
class_setVersion=function(_8bc,_8bd){
_8bc.version=parseInt(_8bd,10);
};
class_replaceMethod=function(_8be,_8bf,_8c0){
if(!_8be||!_8bf){
return NULL;
}
var _8c1=_8be.method_dtable[_8bf],_8c2=_8c1.method_imp,_8c3=new objj_method(_8c1.method_name,_8c0,_8c1.method_types);
_8c3.displayName=_8c1.displayName;
_8be.method_dtable[_8bf]=_8c3;
var _8c4=_8be.method_list.indexOf(_8c1);
if(_8c4!==-1){
_8be.method_list[_8c4]=_8c3;
}else{
_8be.method_list.push(_8c3);
}
return _8c2;
};
class_addProtocol=function(_8c5,_8c6){
if(!_8c6||class_conformsToProtocol(_8c5,_8c6)){
return;
}
(_8c5.protocol_list||(_8c5.protocol_list=[])).push(_8c6);
return true;
};
class_conformsToProtocol=function(_8c7,_8c8){
if(!_8c8){
return false;
}
while(_8c7){
var _8c9=_8c7.protocol_list,size=_8c9?_8c9.length:0;
for(var i=0;i<size;i++){
var p=_8c9[i];
if(p.name===_8c8.name){
return true;
}
if(protocol_conformsToProtocol(p,_8c8)){
return true;
}
}
_8c7=class_getSuperclass(_8c7);
}
return false;
};
class_copyProtocolList=function(_8ca){
var _8cb=_8ca.protocol_list;
return _8cb?_8cb.slice(0):[];
};
protocol_conformsToProtocol=function(p1,p2){
if(!p1||!p2){
return false;
}
if(p1.name===p2.name){
return true;
}
var _8cc=p1.protocol_list,size=_8cc?_8cc.length:0;
for(var i=0;i<size;i++){
var p=_8cc[i];
if(p.name===p2.name){
return true;
}
if(protocol_conformsToProtocol(p,p2)){
return true;
}
}
return false;
};
var _8cd=Object.create(null);
objj_allocateProtocol=function(_8ce){
var _8cf=new objj_protocol(_8ce);
return _8cf;
};
objj_registerProtocol=function(_8d0){
_8cd[_8d0.name]=_8d0;
};
protocol_getName=function(_8d1){
return _8d1.name;
};
protocol_addMethodDescription=function(_8d2,_8d3,_8d4,_8d5,_8d6){
if(!_8d2||!_8d3){
return;
}
if(_8d5){
(_8d6?_8d2.instance_methods:_8d2.class_methods)[_8d3]=new objj_method(_8d3,null,_8d4);
}
};
protocol_addMethodDescriptions=function(_8d7,_8d8,_8d9,_8da){
if(!_8d9){
return;
}
var _8db=0,_8dc=_8d8.length,_8dd=_8da?_8d7.instance_methods:_8d7.class_methods;
for(;_8db<_8dc;++_8db){
var _8de=_8d8[_8db];
_8dd[_8de.method_name]=_8de;
}
};
protocol_copyMethodDescriptionList=function(_8df,_8e0,_8e1){
if(!_8e0){
return [];
}
var _8e2=_8e1?_8df.instance_methods:_8df.class_methods,_8e3=[];
for(var _8e4 in _8e2){
if(_8e2.hasOwnProperty(_8e4)){
_8e3.push(_8e2[_8e4]);
}
}
return _8e3;
};
protocol_addProtocol=function(_8e5,_8e6){
if(!_8e5||!_8e6){
return;
}
(_8e5.protocol_list||(_8e5.protocol_list=[])).push(_8e6);
};
var _8e7=Object.create(null);
objj_allocateTypeDef=function(_8e8){
var _8e9=new objj_typeDef(_8e8);
return _8e9;
};
objj_registerTypeDef=function(_8ea){
_8e7[_8ea.name]=_8ea;
};
typeDef_getName=function(_8eb){
return _8eb.name;
};
var _8ec=function(_8ed){
var meta=_8ed.info&_886?_8ed:_8ed.isa;
if(_8ed.info&_886){
_8ed=objj_getClass(_8ed.name);
}
if(_8ed.super_class&&!((_8ed.super_class.info&_886?_8ed.super_class:_8ed.super_class.isa).info&_887)){
_8ec(_8ed.super_class);
}
if(!(meta.info&_887)&&!(meta.info&_888)){
meta.info=(meta.info|_888)&~0;
_8ed.objj_msgSend=objj_msgSendFast;
_8ed.objj_msgSend0=objj_msgSendFast0;
_8ed.objj_msgSend1=objj_msgSendFast1;
_8ed.objj_msgSend2=objj_msgSendFast2;
_8ed.objj_msgSend3=objj_msgSendFast3;
meta.objj_msgSend=objj_msgSendFast;
meta.objj_msgSend0=objj_msgSendFast0;
meta.objj_msgSend1=objj_msgSendFast1;
meta.objj_msgSend2=objj_msgSendFast2;
meta.objj_msgSend3=objj_msgSendFast3;
_8ed.method_msgSend=_8ed.method_dtable;
meta.method_msgSend=meta.method_dtable;
meta.objj_msgSend0(_8ed,"initialize");
meta.info=(meta.info|_887)&~_888;
}
};
_objj_forward=function(self,_8ee){
var isa=self.isa,meta=isa.info&_886?isa:isa.isa;
if(!(meta.info&_887)&&!(meta.info&_888)){
_8ec(isa);
}
var _8ef=isa.method_msgSend[_8ee];
if(_8ef){
return _8ef.apply(isa,arguments);
}
_8ef=isa.method_dtable[_8f0];
if(_8ef){
var _8f1=_8ef(self,_8f0,_8ee);
if(_8f1&&_8f1!==self){
arguments[0]=_8f1;
return _8f1.isa.objj_msgSend.apply(_8f1.isa,arguments);
}
}
_8ef=isa.method_dtable[_8f2];
if(_8ef){
var _8f3=isa.method_dtable[_8f4];
if(_8f3){
var _8f5=_8ef(self,_8f2,_8ee);
if(_8f5){
var _8f6=objj_lookUpClass("CPInvocation");
if(_8f6){
var _8f7=_8f6.isa.objj_msgSend1(_8f6,_8f8,_8f5),_a0=0,_8f9=arguments.length;
if(_8f7!=null){
var _8fa=_8f7.isa;
for(;_a0<_8f9;++_a0){
_8fa.objj_msgSend2(_8f7,_8fb,arguments[_a0],_a0);
}
}
_8f3(self,_8f4,_8f7);
return _8f7==null?null:_8fa.objj_msgSend0(_8f7,_8fc);
}
}
}
}
_8ef=isa.method_dtable[_8fd];
if(_8ef){
return _8ef(self,_8fd,_8ee);
}
throw class_getName(isa)+" does not implement doesNotRecognizeSelector:. Did you forget a superclass for "+class_getName(isa)+"?";
};
class_getMethodImplementation=function(_8fe,_8ff){
if(!((_8fe.info&_886?_8fe:_8fe.isa).info&_887)){
_8ec(_8fe);
}
var _900=_8fe.method_dtable[_8ff]||_objj_forward;
return _900;
};
var _901=Object.create(null);
objj_enumerateClassesUsingBlock=function(_902){
for(var key in _901){
_902(_901[key]);
}
};
objj_allocateClassPair=function(_903,_904){
var _905=new objj_class(_904),_906=new objj_class(_904),_907=_905;
if(_903){
_907=_903;
while(_907.superclass){
_907=_907.superclass;
}
_905.allocator.prototype=new _903.allocator();
_905.ivar_dtable=_905.ivar_store.prototype=new _903.ivar_store();
_905.method_dtable=_905.method_store.prototype=new _903.method_store();
_906.method_dtable=_906.method_store.prototype=new _903.isa.method_store();
_905.super_class=_903;
_906.super_class=_903.isa;
}else{
_905.allocator.prototype=new objj_object();
}
_905.isa=_906;
_905.name=_904;
_905.info=_885;
_905._UID=objj_generateObjectUID();
_905.init=true;
_906.isa=_907.isa;
_906.name=_904;
_906.info=_886;
_906._UID=objj_generateObjectUID();
_906.init=true;
return _905;
};
var _80a=nil;
objj_registerClassPair=function(_908){
_1[_908.name]=_908;
_901[_908.name]=_908;
_1eb(_908,_80a);
};
objj_resetRegisterClasses=function(){
for(var key in _901){
delete _1[key];
}
_901=Object.create(null);
_8cd=Object.create(null);
_8e7=Object.create(null);
_1ee();
};
class_createInstance=function(_909){
if(!_909){
throw new Error("*** Attempting to create object with Nil class.");
}
var _90a=new _909.allocator();
_90a.isa=_909;
_90a._UID=objj_generateObjectUID();
return _90a;
};
var _90b=function(){
};
_90b.prototype.member=false;
with(new _90b()){
member=true;
}
if((new _90b()).member){
var _90c=class_createInstance;
class_createInstance=function(_90d){
var _90e=_90c(_90d);
if(_90e){
var _90f=_90e.isa,_910=_90f;
while(_90f){
var _911=_90f.ivar_list,_912=_911.length;
while(_912--){
_90e[_911[_912].name]=NULL;
}
_90f=_90f.super_class;
}
_90e.isa=_910;
}
return _90e;
};
}
object_getClassName=function(_913){
if(!_913){
return "";
}
var _914=_913.isa;
return _914?class_getName(_914):"";
};
objj_lookUpClass=function(_915){
var _916=_901[_915];
return _916?_916:Nil;
};
objj_getClass=function(_917){
var _918=_901[_917];
if(!_918){
}
return _918?_918:Nil;
};
objj_getClassList=function(_919,_91a){
for(var _91b in _901){
_919.push(_901[_91b]);
if(_91a&&--_91a===0){
break;
}
}
return _919.length;
};
objj_getMetaClass=function(_91c){
var _91d=objj_getClass(_91c);
return _91d.info&_886?_91d:_91d.isa;
};
objj_getProtocol=function(_91e){
return _8cd[_91e];
};
objj_getTypeDef=function(_91f){
return _8e7[_91f];
};
ivar_getName=function(_920){
return _920.name;
};
ivar_getTypeEncoding=function(_921){
return _921.type;
};
objj_msgSend=function(_922,_923){
if(_922==nil){
return nil;
}
var isa=_922.isa;
if(isa.init){
_8ec(isa);
}
var _924=isa.method_dtable[_923];
var _925=_924?_924.method_imp:_objj_forward;
switch(arguments.length){
case 2:
return _925(_922,_923);
case 3:
return _925(_922,_923,arguments[2]);
case 4:
return _925(_922,_923,arguments[2],arguments[3]);
case 5:
return _925(_922,_923,arguments[2],arguments[3],arguments[4]);
case 6:
return _925(_922,_923,arguments[2],arguments[3],arguments[4],arguments[5]);
case 7:
return _925(_922,_923,arguments[2],arguments[3],arguments[4],arguments[5],arguments[6]);
}
return _925.apply(_922,arguments);
};
objj_msgSendSuper=function(_926,_927){
var _928=_926.super_class;
arguments[0]=_926.receiver;
if(!((_928.info&_886?_928:_928.isa).info&_887)){
_8ec(_928);
}
var _929=_928.method_dtable[_927]||_objj_forward;
return _929.apply(_926.receiver,arguments);
};
objj_msgSendSuper0=function(_92a,_92b){
return (_92a.super_class.method_dtable[_92b]||_objj_forward)(_92a.receiver,_92b);
};
objj_msgSendSuper1=function(_92c,_92d,arg0){
return (_92c.super_class.method_dtable[_92d]||_objj_forward)(_92c.receiver,_92d,arg0);
};
objj_msgSendSuper2=function(_92e,_92f,arg0,arg1){
return (_92e.super_class.method_dtable[_92f]||_objj_forward)(_92e.receiver,_92f,arg0,arg1);
};
objj_msgSendSuper3=function(_930,_931,arg0,arg1,arg2){
return (_930.super_class.method_dtable[_931]||_objj_forward)(_930.receiver,_931,arg0,arg1,arg2);
};
objj_msgSendFast=function(_932,_933){
return (this.method_dtable[_933]||_objj_forward).apply(_932,arguments);
};
var _934=function(_935,_936){
_8ec(this);
return this.objj_msgSend.apply(this,arguments);
};
objj_msgSendFast0=function(_937,_938){
return (this.method_dtable[_938]||_objj_forward)(_937,_938);
};
var _939=function(_93a,_93b){
_8ec(this);
return this.objj_msgSend0(_93a,_93b);
};
objj_msgSendFast1=function(_93c,_93d,arg0){
return (this.method_dtable[_93d]||_objj_forward)(_93c,_93d,arg0);
};
var _93e=function(_93f,_940,arg0){
_8ec(this);
return this.objj_msgSend1(_93f,_940,arg0);
};
objj_msgSendFast2=function(_941,_942,arg0,arg1){
return (this.method_dtable[_942]||_objj_forward)(_941,_942,arg0,arg1);
};
var _943=function(_944,_945,arg0,arg1){
_8ec(this);
return this.objj_msgSend2(_944,_945,arg0,arg1);
};
objj_msgSendFast3=function(_946,_947,arg0,arg1,arg2){
return (this.method_dtable[_947]||_objj_forward)(_946,_947,arg0,arg1,arg2);
};
var _948=function(_949,_94a,arg0,arg1,arg2){
_8ec(this);
return this.objj_msgSend3(_949,_94a,arg0,arg1,arg2);
};
method_getName=function(_94b){
return _94b.method_name;
};
method_copyReturnType=function(_94c){
var _94d=_94c.method_types;
if(_94d){
var _94e=_94d[0];
return _94e!=NULL?_94e:NULL;
}else{
return NULL;
}
};
method_copyArgumentType=function(_94f,_950){
switch(_950){
case 0:
return "id";
case 1:
return "SEL";
default:
var _951=_94f.method_types;
if(_951){
var _952=_951[_950-1];
return _952!=NULL?_952:NULL;
}else{
return NULL;
}
}
};
method_getNumberOfArguments=function(_953){
var _954=_953.method_types;
return _954?_954.length+1:(_953.method_name.match(/:/g)||[]).length+2;
};
method_getImplementation=function(_955){
return _955.method_imp;
};
method_setImplementation=function(_956,_957){
var _958=_956.method_imp;
_956.method_imp=_957;
return _958;
};
method_exchangeImplementations=function(lhs,rhs){
var _959=method_getImplementation(lhs),_95a=method_getImplementation(rhs);
method_setImplementation(lhs,_95a);
method_setImplementation(rhs,_959);
};
sel_getName=function(_95b){
return _95b?_95b:"<null selector>";
};
sel_getUid=function(_95c){
return _95c;
};
sel_isEqual=function(lhs,rhs){
return lhs===rhs;
};
sel_registerName=function(_95d){
return _95d;
};
objj_class.prototype.toString=objj_object.prototype.toString=function(){
var isa=this.isa;
if(class_getInstanceMethod(isa,_95e)){
return isa.objj_msgSend0(this,_95e);
}
if(class_isMetaClass(isa)){
return this.name;
}
return "["+isa.name+" Object](-description not implemented)";
};
objj_class.prototype.objj_msgSend=_934;
objj_class.prototype.objj_msgSend0=_939;
objj_class.prototype.objj_msgSend1=_93e;
objj_class.prototype.objj_msgSend2=_943;
objj_class.prototype.objj_msgSend3=_948;
objj_class.prototype.method_msgSend=Object.create(null);
var _95e=sel_getUid("description"),_8f0=sel_getUid("forwardingTargetForSelector:"),_8f2=sel_getUid("methodSignatureForSelector:"),_8f4=sel_getUid("forwardInvocation:"),_8fd=sel_getUid("doesNotRecognizeSelector:"),_8f8=sel_getUid("invocationWithMethodSignature:"),_95f=sel_getUid("setTarget:"),_960=sel_getUid("setSelector:"),_8fb=sel_getUid("setArgument:atIndex:"),_8fc=sel_getUid("returnValue");
objj_eval=function(_961){
var url=_2.pageURL;
var _962=_2.asyncLoader;
_2.asyncLoader=NO;
var _963=_2.preprocess(_961,url,0);
if(!_963.hasLoadedFileDependencies()){
_963.loadFileDependencies();
}
_1._objj_eval_scope={};
_1._objj_eval_scope.objj_executeFile=_306.fileExecuterForURL(url);
_1._objj_eval_scope.objj_importFile=_306.fileImporterForURL(url);
var code="with(_objj_eval_scope){"+_963._code+"\n//*/\n}";
var _964;
_964=eval(code);
_2.asyncLoader=_962;
return _964;
};
_2.objj_eval=objj_eval;
_17d();
var _965=new CFURL(window.location.href),_966=document.getElementsByTagName("base"),_967=_966.length;
if(_967>0){
var _968=_966[_967-1],_969=_968&&_968.getAttribute("href");
if(_969){
_965=new CFURL(_969,_965);
}
}
if(typeof OBJJ_COMPILER_FLAGS!=="undefined"){
var _96a={};
for(var i=0;i<OBJJ_COMPILER_FLAGS.length;i++){
switch(OBJJ_COMPILER_FLAGS[i]){
case "IncludeDebugSymbols":
_96a.includeMethodFunctionNames=true;
break;
case "IncludeTypeSignatures":
_96a.includeIvarTypeSignatures=true;
_96a.includeMethodArgumentTypeSignatures=true;
break;
case "InlineMsgSend":
_96a.inlineMsgSendFunctions=true;
break;
case "SourceMap":
_96a.sourceMap=true;
break;
}
}
_808.setCurrentCompilerFlags(_96a);
}
var _96b=new CFURL(window.OBJJ_MAIN_FILE||"main.j"),_1ea=(new CFURL(".",new CFURL(_96b,_965))).absoluteURL(),_96c=(new CFURL("..",_1ea)).absoluteURL();
if(_1ea===_96c){
_96c=new CFURL(_96c.schemeAndAuthority());
}
_1cd.resourceAtURL(_96c,YES);
_2.pageURL=_965;
_2.bootstrap=function(){
_96d();
};
function _96d(){
_1cd.resolveResourceAtURL(_1ea,YES,function(_96e){
var _96f=_1cd.includeURLs(),_a0=0,_970=_96f.length;
for(;_a0<_970;++_a0){
_96e.resourceAtURL(_96f[_a0],YES);
}
_306.fileImporterForURL(_1ea)(_96b.lastPathComponent(),YES,function(){
_17e();
_976(function(){
var _971=window.location.hash.substring(1),args=[];
if(_971.length){
args=_971.split("/");
for(var i=0,_970=args.length;i<_970;i++){
args[i]=decodeURIComponent(args[i]);
}
}
var _972=(window.location.search.substring(1)).split("&"),_973=new CFMutableDictionary();
for(var i=0,_970=_972.length;i<_970;i++){
var _974=_972[i].split("=");
if(!_974[0]){
continue;
}
if(_974[1]==null){
_974[1]=true;
}
_973.setValueForKey(decodeURIComponent(_974[0]),decodeURIComponent(_974[1]));
}
main(args,_973);
});
});
});
};
var _975=NO;
function _976(_977){
if(_975||document.readyState==="complete"){
return _977();
}
if(window.addEventListener){
window.addEventListener("load",_977,NO);
}else{
if(window.attachEvent){
window.attachEvent("onload",_977);
}
}
};
_976(function(){
_975=YES;
});
if(typeof OBJJ_AUTO_BOOTSTRAP==="undefined"||OBJJ_AUTO_BOOTSTRAP){
_2.bootstrap();
}
function _1e4(aURL){
if(aURL instanceof CFURL&&aURL.scheme()){
return aURL;
}
return new CFURL(aURL,_1ea);
};
objj_importFile=_306.fileImporterForURL(_1ea);
objj_executeFile=_306.fileExecuterForURL(_1ea);
objj_import=function(){
CPLog.warn("objj_import is deprecated, use objj_importFile instead");
objj_importFile.apply(this,arguments);
};
})(window,ObjectiveJ);
