#  역방향: 공공체육시설/10만(가설 −, 관측 +), 검진 수검률(가설 −, 관측 +).
#  사용(01_스크립트/): TAG=LIPS ST_VER=std3 ST_GRAPH=<graph_593> ./rslot.sh Rscript 88S_lips_reverse_posthoc.R → results_std3/S46_lips_posthoc.csv
suppressPackageStartupMessages({library(INLA);library(sf);library(jsonlite)})
TAG<-Sys.getenv("TAG","LIPS");VER<-Sys.getenv("ST_VER","std3");inla.setOption(num.threads="1:1")
OUTD<-file.path("..","04_분석",TAG);RES<-file.path(OUTD,paste0("results_",VER))
SHP<-Sys.getenv("ST_SHP",file.path(normalizePath(file.path(dirname(sub("--file=","",grep("--file=",commandArgs(),value=TRUE))),"..")),"data","boundary","final.shp"))
S<-fromJSON(file.path(OUTD,sprintf("config_%s_%s.json",TAG,VER)),simplifyVector=TRUE)
DD<-read.csv(file.path(OUTD,sprintf("panel_%s_%s.csv",TAG,VER)),fileEncoding="UTF-8-BOM",stringsAsFactors=FALSE);DD$fbd_region<-enc2utf8(DD$fbd_region)
G<-st_read(SHP,quiet=TRUE);G$region<-enc2utf8(G$region);g<-inla.read.graph(Sys.getenv("ST_GRAPH"));stopifnot(g$n==nrow(G))
DD$area<-match(DD$fbd_region,G$region);DD$time<-DD$year-min(DD$year)+1;DD$yiid<-DD$time
FORCED<-S$forced;HYP<-as.character(S$sets_after_vif$S1_narrative_full)
pc<-list(prec=list(prior="pc.prec",param=c(0.5,0.01)),phi=list(prior="pc",param=c(0.5,2/3)));pcp<-list(prec=list(prior="pc.prec",param=c(0.5,0.01)))
z<-function(x)(x-mean(x))/sd(x)
fit<-function(vars){f<-as.formula(paste("cases ~ 1 +",paste(sprintf("`%s`",vars),collapse="+"),"+ f(area,model='bym2',graph=g,scale.model=TRUE,constr=TRUE,hyper=pc) + f(time,model='rw1',scale.model=TRUE,hyper=pcp) + f(yiid,model='iid',hyper=pcp)"))
  inla(f,family="nbinomial",data=DD,E=DD$E,control.fixed=list(mean=0,prec=4,mean.intercept=0,prec.intercept=0.001),control.compute=list(waic=TRUE),control.inla=list(control.vb=list(emergency=50)))}
out<-NULL
add<-function(an,m,vs){fx<-m$summary.fixed;for(v in vs){if(!v%in%rownames(fx))next;r<-fx[v,];out<<-rbind(out,data.frame(analysis=an,cov=v,IRR=round(exp(r$mean),4),lo=round(exp(r$`0.025quant`),4),hi=round(exp(r$`0.975quant`),4),cred=(exp(r$`0.025quant`)>1|exp(r$`0.975quant`)<1),WAIC=round(m$waic$waic,1)))};cat(an,"done\n")}
z<-function(x)(x-mean(x))/sd(x)
F1<-"ext__public_sport_fac_per100k";F2<-"ext__screening_uptake";REV<-c(F1,F2)
DD$popdens_log<-z(log(DD$population/(DD$area_m2/1e6)))
DD$sportfac_per_km2_log<-z(log1p(DD[[paste0(F1,"_raw")]]*DD$population/1e5/(DD$area_m2/1e6)))
for(v in REV){m<-ave(DD[[v]],DD$fbd_region);DD[[paste0(v,"__B")]]<-(m-mean(m))/sd(m);w<-DD[[v]]-m;DD[[paste0(v,"__W")]]<-w/sd(w)}
MAIN<-unique(c(HYP,FORCED));SENS<-intersect(c("tertiary_educated_share","ext__unmet_need_rate","ext__living_alone_elderly"),names(DD))
add("P0_main",fit(MAIN),REV)
add("P1_plus_sensitivity_vars",fit(c(MAIN,SENS)),c(REV,SENS))
add("P2a_sportfac_alone",fit(c(F1,FORCED)),F1)
add("P2b_uptake_alone",fit(c(F2,FORCED)),F2)
add("P3_plus_popdens",fit(c(MAIN,"popdens_log")),c(REV,"popdens_log"))
BW<-c(setdiff(MAIN,REV),paste0(REV,"__B"),paste0(REV,"__W"));add("P4_between_within",fit(BW),c(paste0(REV,"__B"),paste0(REV,"__W")))
add("P5_sportfac_per_km2",fit(c(setdiff(MAIN,F1),"sportfac_per_km2_log")),c("sportfac_per_km2_log",F2))
add("P5b_per100k_and_per_km2",fit(c(MAIN,"sportfac_per_km2_log")),c(F1,"sportfac_per_km2_log"))
add("P6_drop_uptake",fit(setdiff(MAIN,F2)),F1)
add("P7_drop_sportfac",fit(setdiff(MAIN,F1)),F2)
dx<-DD;dx$cases[dx$year%in%2020:2021]<-NA;DD0<-DD;DD<-dx;add("P8_excl_2020_2021",fit(MAIN),c(REV,"ext__walking_rate"));DD<-DD0
DD$sportfac_log<-z(log1p(DD[[paste0(F1,"_raw")]]));add("P9_sportfac_log",fit(c(setdiff(MAIN,F1),"sportfac_log")),c("sportfac_log",F2))
write.csv(out,file.path(RES,"S46_lips_posthoc.csv"),row.names=FALSE);print(out)
