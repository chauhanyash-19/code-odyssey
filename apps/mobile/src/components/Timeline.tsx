import React from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';
import { Colors, Fonts } from '../constants/Colors';

interface TimelineStep {
  title: string;
  subtitle: string;
}

const Timeline: React.FC = () => {
  const steps: TimelineStep[] = [
    {
      title: 'Audio Captured',
      subtitle: 'Call stream secured & buffered locally',
    },
    {
      title: 'DSP Analysis',
      subtitle: 'Signal cleaned, frequencies isolated',
    },
    {
      title: 'Deepfake Scan',
      subtitle: 'Voice compared against synthetic patterns',
    },
    {
      title: 'Fact Verification',
      subtitle: 'Claims checked against trusted sources',
    },
    {
      title: 'Final Risk Score',
      subtitle: 'Composite score delivered in real time',
    },
  ];

  const [visibleSteps, setVisibleSteps] = React.useState<boolean[]>(
    Array(steps.length).fill(false)
  );

  React.useEffect(() => {
    steps.forEach((_, idx) => {
      setTimeout(() => {
        setVisibleSteps((prev) => {
          const newState = [...prev];
          newState[idx] = true;
          return newState;
        });
      }, idx * 120);
    });
  }, [steps.length]);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.titleBar} />
        <Text style={styles.title}>AI Detection Timeline</Text>
      </View>

      <View style={styles.timelineList}>
        {steps.map((step, idx) => (
          <Animated.View
            key={idx}
            style={[
              styles.step,
              {
                opacity: visibleSteps[idx] ? 1 : 0,
                transform: [
                  {
                    translateX: visibleSteps[idx] ? 0 : -8,
                  },
                ],
              },
            ]}
          >
            <View style={styles.dot} />
            <View style={styles.content}>
              <Text style={styles.stepTitle}>{step.title}</Text>
              <Text style={styles.stepSub}>{step.subtitle}</Text>
            </View>
          </Animated.View>
        ))}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginHorizontal: 20,
    marginBottom: 30,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 14,
  },
  titleBar: {
    width: 3,
    height: 14,
    borderRadius: 2,
    backgroundColor: Colors.lightBlue,
  },
  title: {
    fontFamily: Fonts.display,
    fontSize: 14,
    fontWeight: '600',
    color: Colors.white,
  },
  timelineList: {
    paddingLeft: 26,
    borderLeftWidth: 1.5,
    borderLeftColor: Colors.accentBlue,
    paddingVertical: 4,
  },
  step: {
    flexDirection: 'row',
    paddingBottom: 22,
  },
  dot: {
    position: 'absolute',
    left: -26,
    top: 1,
    width: 13,
    height: 13,
    borderRadius: 6.5,
    backgroundColor: Colors.bgPrimary,
    borderWidth: 2,
    borderColor: Colors.accentBlue,
    shadowColor: Colors.accentBlue,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 8,
    elevation: 3,
  },
  content: {
    flex: 1,
  },
  stepTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: Colors.white,
    marginBottom: 2,
    fontFamily: Fonts.display,
  },
  stepSub: {
    fontSize: 10.5,
    color: Colors.mediumBlue,
    fontFamily: Fonts.body,
  },
});

export default Timeline;
