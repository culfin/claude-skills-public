<?php
/**
 * Registers the course post type. The topic taxonomy is registered by a companion plugin
 * ("course-topics"), which site owners may deactivate.
 */

defined( 'ABSPATH' ) || exit;

add_action(
	'init',
	static function (): void {
		register_post_type(
			CT_POST_TYPE,
			[
				'label'        => __( 'Courses', 'ct' ),
				'public'       => true,
				'has_archive'  => false,
				'show_in_rest' => true,
				'supports'     => [ 'title', 'editor', 'thumbnail' ],
				'rewrite'      => [ 'slug' => 'courses' ],
			]
		);
	}
);

add_filter(
	'the_content',
	static function ( string $content ): string {
		if ( ! is_singular( CT_POST_TYPE ) ) {
			return $content;
		}
		$course = ct_shape( get_the_ID() );
		if ( null === $course ) {
			return $content;
		}
		$topics = '';
		foreach ( $course['topics'] as $topic ) {
			$topics .= '<li>' . esc_html( $topic ) . '</li>';
		}
		return $content . ( '' !== $topics ? '<ul class="ct-topics">' . $topics . '</ul>' : '' );
	}
);
