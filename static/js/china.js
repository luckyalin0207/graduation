/*
* Licensed to the Apache Software Foundation (ASF) under one
* or more contributor license agreements.  See the NOTICE file
* distributed with this work for additional information
* regarding copyright ownership.  The ASF licenses this file
* to you under the Apache License, Version 2.0 (the
* "License"); you may not use this file except in compliance
* with the License.  You may obtain a copy of the License at
*
*   http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing,
* software distributed under the License is distributed on an
* "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
* KIND, either express or implied.  See the License for the
* specific language governing permissions and limitations
* under the License.
*/

(function(root, factory) {
    if (typeof define === 'function' && define.amd) {
        // AMD. Register as an anonymous module.
        define(['exports', 'echarts'], factory);
    } else if (
        typeof exports === 'object' &&
        typeof exports.nodeName !== 'string'
    ) {
        // CommonJS
        factory(exports, require('echarts'));
    } else {
        // Browser globals
        factory({}, root.echarts);
    }
})(this, function(exports, echarts) {
    var log = function(msg) {
        if (typeof console !== 'undefined') {
            console && console.error && console.error(msg);
        }
    };
    if (!echarts) {
        log('ECharts is not Loaded');
        return;
    }
    if (!echarts.registerMap) {
        log('ECharts Map is not loaded');
        return;
    }
    echarts.registerMap('china', {
        type: 'FeatureCollection',
        features: [
            {
                id: '710000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@°Ü¯Û'],
                        [
                            '@@ƛĴÕƊÉɘǢŊơŬŮȠÿ¥ͪǿ¾ąʷƏÒÝǨt°'
                        ]
                    ],
                    encodeOffsets: [[[122886, 24033]], [[123335, 22980]]]
                },
                properties: {
                    cp: [121.0254, 23.5986],
                    name: '台湾',
                    childNum: 2
                }
            },
            {
                id: '130000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@o~Z]ªrºc_ħ'],
                        ['@@Ĉě§ª']
                    ],
                    encodeOffsets: [[[120023, 41045]], [[121615, 39415]]]
                },
                properties: {
                    cp: [114.502461, 38.045474],
                    name: '河北',
                    childNum: 2
                }
            },
            {
                id: '140000',
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: ['@@ÞĩÒSµ'],
                    encodeOffsets: [[116874, 41716]]
                },
                properties: {
                    cp: [112.549248, 37.857014],
                    name: '山西',
                    childNum: 1
                }
            },
            {
                id: '150000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@Çđc̓o§'],
                        ['@@Åw^ÏNÁ`']
                    ],
                    encodeOffsets: [[[126019, 45915]], [[118846, 42767]]]
                },
                properties: {
                    cp: [111.670801, 40.818311],
                    name: '内蒙古',
                    childNum: 2
                }
            },
            {
                id: '210000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@L̑ËÁ'],
                        ['@@Ñľģȋß']
                    ],
                    encodeOffsets: [[[123686, 42662]], [[126019, 40435]]]
                },
                properties: {
                    cp: [123.429096, 41.796767],
                    name: '辽宁',
                    childNum: 2
                }
            },
            {
                id: '220000',
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: ['@@ìwc¢v'],
                    encodeOffsets: [[130123, 42689]]
                },
                properties: {
                    cp: [125.3245, 43.886841],
                    name: '吉林',
                    childNum: 1
                }
            },
            {
                id: '230000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@ƨĶ²ġw'],
                        ['@@UµNÿ¾']
                    ],
                    encodeOffsets: [[[127123, 51780]], [[134456, 44547]]]
                },
                properties: {
                    cp: [126.642464, 45.756967],
                    name: '黑龙江',
                    childNum: 2
                }
            },
            {
                id: '320000',
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: ['@@cþÞ^ªá'],
                    encodeOffsets: [[121740, 32276]]
                },
                properties: {
                    cp: [118.767413, 32.041544],
                    name: '江苏',
                    childNum: 1
                }
            },
            {
                id: '330000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@jX^j'],
                        ['@@sfdM'],
                        ['@@qP\\xz[ck'],
                        ['@@R¦w\\lļǏ'],
                        ['@@Hi«]Zw']
                    ],
                    encodeOffsets: [
                        [[125592, 31553]],
                        [[125785, 29543]],
                        [[125729, 30690]],
                        [[125513, 30171]],
                        [[125223, 30438]]
                    ]
                },
                properties: {
                    cp: [120.153576, 30.287459],
                    name: '浙江',
                    childNum: 5
                }
            },
            {
                id: '340000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@^¯jÕ~'],
                        ['@@H«ÅX']
                    ],
                    encodeOffsets: [[[117416, 31519]], [[118450, 32760]]]
                },
                properties: {
                    cp: [117.283042, 31.86119],
                    name: '安徽',
                    childNum: 2
                }
            },
            {
                id: '350000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@zht´]'],
                        ['@@aj^~ĆG©O'],
                        ['@@ed¨C]]'],
                        ['@@e©Ehl'],
                        ['@@ux[l]']
                    ],
                    encodeOffsets: [
                        [[122321, 28380]],
                        [[122541, 27268]],
                        [[123012, 25474]],
                        [[122952, 26357]],
                        [[122885, 25112]]
                    ]
                },
                properties: {
                    cp: [119.306239, 26.075302],
                    name: '福建',
                    childNum: 5
                }
            },
            {
                id: '360000',
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: ['@@ĢĨĂâĶRå'],
                    encodeOffsets: [[118923, 30536]]
                },
                properties: {
                    cp: [115.892151, 28.676493],
                    name: '江西',
                    childNum: 1
                }
            },
            {
                id: '370000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@Xjd]{K'],
                        ['@@itbFHy'],
                        ['@@Ny}B']
                    ],
                    encodeOffsets: [
                        [[121014, 37039]],
                        [[123150, 36831]],
                        [[119706, 36877]]
                    ]
                },
                properties: {
                    cp: [117.000923, 36.675807],
                    name: '山东',
                    childNum: 3
                }
            },
            {
                id: '410000',
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: ['@@ýLùµP³'],
                    encodeOffsets: [[118256, 37017]]
                },
                properties: {
                    cp: [113.665412, 34.757975],
                    name: '河南',
                    childNum: 1
                }
            },
            {
                id: '420000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@AB'],
                        ['@@lskt']
                    ],
                    encodeOffsets: [[[115920, 30562]], [[113852, 31379]]]
                },
                properties: {
                    cp: [114.298572, 30.584355],
                    name: '湖北',
                    childNum: 2
                }
            },
            {
                id: '430000',
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: ['@@vßwĝ'],
                    encodeOffsets: [[114725, 30427]]
                },
                properties: {
                    cp: [112.982279, 28.19409],
                    name: '湖南',
                    childNum: 1
                }
            },
            {
                id: '440000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@QdAsa'],
                        ['@@lxDLo'],
                        ['@@sbhNLo'],
                        ['@@Ă ā']
                    ],
                    encodeOffsets: [
                        [[117381, 22988]],
                        [[116552, 22934]],
                        [[116790, 22617]],
                        [[115612, 22716]]
                    ]
                },
                properties: {
                    cp: [113.280637, 23.125178],
                    name: '广东',
                    childNum: 4
                }
            },
            {
                id: '450000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [['@@H TQ§'], ['@@ĨÊªB']],
                    encodeOffsets: [[[111707, 21520]], [[107619, 25527]]]
                },
                properties: {
                    cp: [108.320004, 22.82402],
                    name: '广西',
                    childNum: 2
                }
            },
            {
                id: '460000',
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: ['@@¶ĲĿê`'],
                    encodeOffsets: [[111707, 21520]]
                },
                properties: {
                    cp: [110.33119, 20.031971],
                    name: '海南',
                    childNum: 1
                }
            },
            {
                id: '510000',
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: ['@@Õg^vÁbnÀ'],
                    encodeOffsets: [[104547, 30384]]
                },
                properties: {
                    cp: [104.065735, 30.659462],
                    name: '四川',
                    childNum: 1
                }
            },
            {
                id: '520000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@G\\lY£in'],
                        ['@@q|mc¯tÏV']
                    ],
                    encodeOffsets: [[[112158, 27383]], [[112105, 27474]]]
                },
                properties: {
                    cp: [106.713478, 26.578343],
                    name: '贵州',
                    childNum: 2
                }
            },
            {
                id: '530000',
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: ['@@[ùx½ÅA@ùÅª'],
                    encodeOffsets: [[101933, 26743]]
                },
                properties: {
                    cp: [102.712251, 25.040609],
                    name: '云南',
                    childNum: 1
                }
            },
            {
                id: '540000',
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: ['@@ÂhľxŊ{Dk'],
                    encodeOffsets: [[88824, 36109]]
                },
                properties: {
                    cp: [91.132212, 29.660361],
                    name: '西藏',
                    childNum: 1
                }
            },
            {
                id: '610000',
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: ['@@p¢ȮµûȩÄ'],
                    encodeOffsets: [[110234, 38774]]
                },
                properties: {
                    cp: [108.948024, 34.263161],
                    name: '陕西',
                    childNum: 1
                }
            },
            {
                id: '620000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@VuǑ'],
                        ['@@þĊĳÏ']
                    ],
                    encodeOffsets: [[[108649, 36281]], [[105636, 38265]]]
                },
                properties: {
                    cp: [103.823557, 36.058039],
                    name: '甘肃',
                    childNum: 2
                }
            },
            {
                id: '630000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@InJm'],
                        ['@@CÆ½OŃĪƗŜ']
                    ],
                    encodeOffsets: [[[105857, 37350]], [[101455, 36373]]]
                },
                properties: {
                    cp: [101.778916, 36.623178],
                    name: '青海',
                    childNum: 2
                }
            },
            {
                id: '640000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [['@@KëÀǻĸ¸'], ['@@RǢǒh']],
                    encodeOffsets: [[[109419, 38041]], [[108522, 37227]]]
                },
                properties: {
                    cp: [106.278179, 38.46637],
                    name: '宁夏',
                    childNum: 2
                }
            },
            {
                id: '650000',
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: ['@@Q¨ªÖpƸ±ü'],
                    encodeOffsets: [[88824, 36109]]
                },
                properties: {
                    cp: [87.617733, 43.792818],
                    name: '新疆',
                    childNum: 1
                }
            },
            {
                id: '110000',
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: ['@@ĪƏÜ'],
                    encodeOffsets: [[120023, 41045]]
                },
                properties: {
                    cp: [116.405285, 39.904989],
                    name: '北京',
                    childNum: 1
                }
            },
            {
                id: '120000',
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: ['@@ňĞƏÛÁ'],
                    encodeOffsets: [[120237, 41215]]
                },
                properties: {
                    cp: [117.190182, 39.125596],
                    name: '天津',
                    childNum: 1
                }
            },
            {
                id: '310000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@ɧư¬EpƸÁx]'],
                        ['@@©ª']
                    ],
                    encodeOffsets: [[[121747, 31822]], [[124701, 32110]]]
                },
                properties: {
                    cp: [121.472644, 31.231706],
                    name: '上海',
                    childNum: 2
                }
            },
            {
                id: '500000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@TÂK'],
                        ['@@ĎJĊ'],
                        ['@@ûT']
                    ],
                    encodeOffsets: [
                        [[109628, 30765]],
                        [[111725, 31320]],
                        [[104707, 31417]]
                    ]
                },
                properties: {
                    cp: [106.504962, 29.533155],
                    name: '重庆',
                    childNum: 3
                }
            },
            {
                id: '810000',
                type: 'Feature',
                geometry: {
                    type: 'MultiPolygon',
                    coordinates: [
                        ['@@AlFi'],
                        ['@@Çw˙DÅÀ'],
                        ['@@ȢVĎÌÜ']
                    ],
                    encodeOffsets: [
                        [[117111, 23002]],
                        [[117072, 22876]],
                        [[117045, 22887]]
                    ]
                },
                properties: {
                    cp: [114.173355, 22.320048],
                    name: '香港',
                    childNum: 3
                }
            },
            {
                id: '820000',
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: ['@@áw{Îr'],
                    encodeOffsets: [[116285, 22746]]
                },
                properties: {
                    cp: [113.54909, 22.198951],
                    name: '澳门',
                    childNum: 1
                }
            }
        ],
        UTF8Encoding: true
    });
}); 